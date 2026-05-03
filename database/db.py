import asyncpg
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- ELITE ARCHITECT SCHEMA ---
SCHEMA_SQL = """
-- 1. USER CORE DATA (Updated with Before Photo)
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    full_name TEXT,
    username TEXT,
    language VARCHAR(2) DEFAULT 'EN',
    
    -- Fitness Baseline
    gender VARCHAR(10),
    age INTEGER,
    phone_number VARCHAR(20),
    current_weight_kg DECIMAL(5, 2),
    
    
    -- Identity Verification
    fayda_file_id TEXT,
    
    -- Legal & Health Compliance
    has_health_clearance BOOLEAN DEFAULT FALSE,
    accepted_terms BOOLEAN DEFAULT FALSE,
    
    -- Status Tracking
    is_paid BOOLEAN DEFAULT FALSE,
    has_joined_group BOOLEAN DEFAULT FALSE,
    registration_step VARCHAR(50) DEFAULT 'start',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. SIMPLIFIED PAYMENT VERIFICATION
CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(telegram_id) ON DELETE CASCADE,
    proof_file_id TEXT NOT NULL, 
    amount DECIMAL(12, 2) DEFAULT 1000.00,
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected
    admin_note TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- 3. GLOBAL CHALLENGE METADATA
CREATE TABLE IF NOT EXISTS challenge_settings (
    key TEXT PRIMARY KEY,
    value_text TEXT,
    value_int INTEGER,
    value_decimal DECIMAL(12, 2)
);

-- PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_users_paid_status ON users (is_paid);
CREATE INDEX IF NOT EXISTS idx_payments_pending_flow ON payments (status) WHERE status = 'pending';
ALTER TABLE users ADD COLUMN IF NOT EXISTS before_photo_file_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS  photo_front_file_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_side_file_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS  photo_rear_file_id TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS processed_by TEXT; 
-- Stores the @username or Name of the admin who clicked approve/reject
"""

class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None
        
    
    async def create_payment(self, user_id: int, proof_file_id: str, amount: float):
        query = """
            INSERT INTO payments (user_id, proof_file_id, amount, status, created_at)
            VALUES ($1, $2, $3, 'pending', CURRENT_TIMESTAMP)
        """
        await self._pool.execute(query, user_id, proof_file_id, amount)

    async def connect(self):
        """Initializes the connection pool for high-concurrency."""
        if not self._pool:
            self._pool = await asyncpg.create_pool(
                self.dsn,
                min_size=2,
                max_size=15, # Scaled for major influencer traffic
                command_timeout=60
            )
            logging.info("DB: Asyncpg pool established.")

    async def setup(self):
        """Initializes the schema and seeds default values."""
        async with self._pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
            # Seed the 900 ETB entry fee
            await conn.execute("""
                INSERT INTO challenge_settings (key, value_decimal) 
                VALUES ('entry_fee', 1000.00) 
                ON CONFLICT DO NOTHING;
            """)
            
    
    async def get_funnel_stats(self) -> Dict[str, Any]:
        # 1. Get raw counts per step
        query = """
            SELECT registration_step, COUNT(*) as count 
            FROM users 
            GROUP BY registration_step
        """
        rows = await self._pool.fetch(query)
        
        # Initialize funnel with 0s
        stats = {
            'start': 0, 'phone': 0, 'gender': 0, 'age': 0, 
            'weight': 0, 'legal': 0, 'payment': 0, 'photo': 0, 
            'verified': 0, 'rejected': 0, 'total': 0, 'revenue': 0
        }

        for row in rows:
            step = row['registration_step']
            # Map photo steps into one 'photo' bucket for simplicity
            if 'photo' in step:
                stats['photo'] += row['count']
            elif step in stats:
                stats[step] += row['count']
            
            stats['total'] += row['count']

        # 2. Get Revenue (Approved payments only)
        rev_query = "SELECT SUM(amount) FROM payments WHERE status = 'approved'"
        revenue = await self._pool.fetchval(rev_query)
        stats['revenue'] = float(revenue or 0.0)

        # 3. Get pending verification count
        pending_query = "SELECT COUNT(*) FROM users WHERE registration_step = 'verification_pending'"
        stats['pending'] = await self._pool.fetchval(pending_query)

        return stats

    # --- USER ENGINE ---
    async def get_user(self, telegram_id: int) -> Optional[asyncpg.Record]:
        return await self._pool.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
    
    
    async def get_system_stats(self):
        """Fetches real-time stats using SQL for PostgreSQL."""
        query = """
            SELECT 
                (SELECT COUNT(*) FROM users) as total,
                (SELECT COUNT(*) FROM users WHERE registration_step = 'verified') as verified,
                (SELECT COUNT(*) FROM users WHERE registration_step = 'verification_pending') as pending,
                (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'approved') as revenue
        """
        # Using the existing pool to fetch a single row
        row = await self._pool.fetchrow(query)
        return dict(row) # Converts asyncpg.Record to a dict: {'total': x, 'verified': y, ...}

    # --- FIXED VERIFIED USERS FETCH ---
    async def get_all_verified_users(self):
        """Fetches all users ready for broadcast."""
        query = "SELECT telegram_id as user_id FROM users WHERE registration_step = 'verified'"
        return await self._pool.fetch(query)

    # --- FIXED SEARCH ENGINE ---
    async def search_users(self, query: str):
        """Searches by name (case-insensitive) or exact phone match using SQL ILIKE."""
        sql = """
            SELECT * FROM users 
            WHERE full_name ILIKE $1 
            OR phone_number LIKE $1
            LIMIT 10
        """
        search_term = f"%{query}%"
        return await self._pool.fetch(sql, search_term)

    # --- FIXED PENDING QUEUE ---
    async def get_pending_users(self):
        """Returns users waiting for verification."""
        query = "SELECT * FROM users WHERE registration_step = 'verification_pending'"
        return await self._pool.fetch(query)

    async def update_user(self, telegram_id: int, **kwargs):
        """Atomic upsert to handle state-based onboarding."""
        if not kwargs:
            return
            
        keys = kwargs.keys()
        values = list(kwargs.values())
        set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(keys)])
        
        query = f"""
            INSERT INTO users (telegram_id, {", ".join(keys)}) 
            VALUES ($1, {", ".join([f"${i+2}" for i in range(len(keys))])})
            ON CONFLICT (telegram_id) DO UPDATE SET {set_clause}
        """
        await self._pool.execute(query, telegram_id, *values)

    # --- PAYMENT ENGINE ---
    async def submit_payment(self, user_id: int, proof_file_id: str, amount: float = 1000.00):
        """Records payment proof for admin review."""
        query = """
            INSERT INTO payments (user_id, proof_file_id, amount)
            VALUES ($1, $2, $3) RETURNING id
        """
        return await self._pool.fetchval(query, user_id, proof_file_id, amount)

    async def get_pending_payments(self, limit: int = 10):
        """Fetches payments for the Admin Dashboard."""
        query = """
            SELECT p.id, p.user_id, p.proof_file_id, u.full_name, u.username
            FROM payments p
            JOIN users u ON p.user_id = u.telegram_id
            WHERE p.status = 'pending'
            ORDER BY p.created_at ASC LIMIT $1
        """
        return await self._pool.fetch(query, limit)

    async def process_payment(self, payment_id: int, status: str, admin_note: str = None):
        """Approves or rejects payment and updates user status in a single transaction."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # 1. Update the payment record
                row = await conn.fetchrow("""
                    UPDATE payments 
                    SET status = $2, admin_note = $3, processed_at = CURRENT_TIMESTAMP 
                    WHERE id = $1 RETURNING user_id
                """, payment_id, status, admin_note)
                
                if row and status == 'approved':
                    # 2. Grant access if approved
                    await conn.execute("UPDATE users SET is_paid = TRUE WHERE telegram_id = $1", row['user_id'])
                    return row['user_id']
        return None

    # --- ANALYTICS ---
    async def get_admin_stats(self):
        """High-level KPI dashboard."""
        query = """
            SELECT 
                (SELECT count(*) FROM users) as total_users,
                (SELECT count(*) FROM users WHERE is_paid = TRUE) as total_paid,
                (SELECT count(*) FROM payments WHERE status = 'pending') as pending_count,
                (SELECT COALESCE(sum(amount), 0) FROM payments WHERE status = 'approved') as revenue
        """
        return await self._pool.fetchrow(query)

    async def disconnect(self):
        if self._pool:
            await self._pool.close()
            
    
    
    # --- SQL FIX FOR BROADCAST ENGINE ---
    async def get_user_count_by_status(self, status: str) -> int:
        """SQL version of count cross-referencing payments and users"""
        
        if status == "all":
            # Total number of unique people who have interacted with the bot
            query = "SELECT COUNT(*) FROM users"
            return await self._pool.fetchval(query)
        elif status == "verified":
                    # Counts unique users who have a payment that is either 'approved' OR 'pending'
                    query = """
                        SELECT COUNT(DISTINCT user_id) 
                        FROM payments 
                        WHERE status IN ('approved', 'pending')
                    """
                    return await self._pool.fetchval(query)

        else: # unverified/incomplete
            # Users who exist in the system but have NO approved payments
            query = """
                SELECT COUNT(*) FROM users 
                WHERE telegram_id NOT IN (
                    SELECT user_id FROM payments WHERE status = 'approved'
                )
            """
            return await self._pool.fetchval(query)

    async def get_users_for_broadcast(self, status: str) -> List[int]:
        """SQL version of fetching IDs for PostgreSQL"""
        if status == "all":
            query = "SELECT telegram_id FROM users"
        elif status == "verified":
            query = "SELECT telegram_id FROM users WHERE registration_step = 'verified'"
        else: # unverified
            query = "SELECT telegram_id FROM users WHERE registration_step != 'verified'"
            
        rows = await self._pool.fetch(query)
        # Convert list of Records to a simple list of integers
        return [row['telegram_id'] for row in rows]