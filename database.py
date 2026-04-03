import aiosqlite
from datetime import datetime

DB_PATH = "bot.db"


async def init_db():
    """Barcha jadvallarni yaratish"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Foydalanuvchilar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                role        TEXT,       -- 'client' yoki 'taxi'
                phone       TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        # Obunalar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                tariff     TEXT,
                start_date TEXT,
                end_date   TEXT,
                status     TEXT DEFAULT 'active',  -- 'active', 'expired'
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        """)

        # To'lovlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                tariff     TEXT,
                amount     INTEGER,
                status     TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        """)

        # Buyurtmalar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id  INTEGER NOT NULL,
                from_loc   TEXT,
                to_loc     TEXT,
                latitude   REAL,
                longitude  REAL,
                gender     TEXT,            -- 'erkak', 'ayol', 'boshqa'
                order_time TEXT,
                price      TEXT,
                phone      TEXT,            -- Ro'yxatdan o'tgan raqam
                contact_phone TEXT,         -- Buyurtma uchun qo'shimcha raqam
                passengers TEXT,
                status     TEXT DEFAULT 'pending',  -- 'pending', 'taken', 'expired', 'cancelled'
                taken_by   INTEGER,
                idempotency_key TEXT UNIQUE,
                rebroadcast_count INTEGER DEFAULT 0,
                cancel_reason TEXT,
                cancel_by     TEXT,         -- 'client', 'driver'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES users(telegram_id)
            )
        """)

        # Bekor qilishlar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cancellations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                role       TEXT,
                order_id   INTEGER,
                reason     TEXT,
                timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Analytics jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT,
                user_id    INTEGER,
                order_id   INTEGER,
                meta       TEXT,            -- JSON string
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Haydovchi lokatsiyalari
        await db.execute("""
            CREATE TABLE IF NOT EXISTS driver_locations (
                user_id    INTEGER PRIMARY KEY,
                latitude   REAL,
                longitude  REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tariflar jadvali (boshqariladigan)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tariffs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                key        TEXT UNIQUE,
                name       TEXT,
                price      INTEGER,
                days       INTEGER
            )
        """)


        # Versiya yangilash (agar ustunlar bo'lmasa qo'shish)
        # Ustunlarni tekshirish va qo'shish (migratsiya)
        migrations = [
            ("orders", "gender", "TEXT"),
            ("orders", "idempotency_key", "TEXT UNIQUE"),
            ("orders", "rebroadcast_count", "INTEGER DEFAULT 0"),
            ("orders", "cancel_reason", "TEXT"),
            ("orders", "cancel_by", "TEXT"),
            ("users", "balance", "INTEGER DEFAULT 0"),
            ("users", "discount_balance", "INTEGER DEFAULT 0")
        ]
        
        for table, column, col_type in migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except aiosqlite.OperationalError:
                pass

        await db.commit()


# ─── USERS ───────────────────────────────────────────────────────────────────

async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            return await cursor.fetchone()


async def upsert_user(telegram_id: int, username: str, full_name: str, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        # Avoid overwriting discount_balance on upsert
        await db.execute("""
            INSERT INTO users (telegram_id, username, full_name, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name,
                role      = excluded.role
        """, (telegram_id, username, full_name, role))
        await db.commit()


async def save_user_phone(telegram_id: int, phone: str, username: str, full_name: str):
    """Save phone number during /start"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, username, full_name, phone)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name,
                phone     = excluded.phone
        """, (telegram_id, username, full_name, phone))
        await db.commit()


async def add_discount_balance(telegram_id: int, amount: int):
    """Haydovchiga chegirma bonusi qo'shish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET discount_balance = COALESCE(discount_balance, 0) + ? 
            WHERE telegram_id = ?
        """, (amount, telegram_id))
        await db.commit()


async def deduct_discount_balance(telegram_id: int, amount: int):
    """Haydovchi obuna sotib olganda bonusi ayriladi"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET discount_balance = COALESCE(discount_balance, 0) - ? 
            WHERE telegram_id = ?
        """, (amount, telegram_id))
        await db.commit()

async def update_balance(telegram_id: int, amount: int):
    """Foydalanuvchi asosiy balansiga pul qo'shish yoki yechish (manfiy amount bilan)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET balance = COALESCE(balance, 0) + ? 
            WHERE telegram_id = ?
        """, (amount, telegram_id))
        await db.commit()

async def get_all_users(role: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM users"
        params = []
        if role:
            query += " WHERE role = ?"
            params.append(role)
        query += " ORDER BY created_at DESC"
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


async def get_user_by_search(search: str):
    """ID yoki Username orqali foydalanuvchini topish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if search.startswith("@"):
            username = search[1:]
            async with db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
                return await cursor.fetchone()
        elif search.isdigit():
            async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (int(search),)) as cursor:
                return await cursor.fetchone()
        return None



async def count_users_by_role(role: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE role = ?", (role,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ─── SUBSCRIPTIONS ────────────────────────────────────────────────────────────

async def get_active_subscription(user_id: int):
    """Foydalanuvchining aktiv obunasini qaytaradi"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM subscriptions
            WHERE user_id = ? AND status = 'active' AND end_date >= datetime('now')
            ORDER BY end_date DESC LIMIT 1
        """, (user_id,)) as cursor:
            return await cursor.fetchone()


async def add_subscription(user_id: int, tariff: str, days: int):
    """Yangi obuna qo'shish"""
    now = datetime.now()
    # Agar mavjud aktiv obuna bo'lsa, uni uzaytirish
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT end_date FROM subscriptions
            WHERE user_id = ? AND status = 'active' AND end_date >= datetime('now')
            ORDER BY end_date DESC LIMIT 1
        """, (user_id,)) as cursor:
            existing = await cursor.fetchone()

        if existing:
            # Mavjud obunani uzaytirish
            from datetime import timedelta
            last_end = datetime.fromisoformat(existing["end_date"])
            new_end = last_end + timedelta(days=days)
            await db.execute("""
                UPDATE subscriptions SET end_date = ? WHERE user_id = ? AND status = 'active'
            """, (new_end.isoformat(), user_id))
        else:
            from datetime import timedelta
            start = now
            end = now + timedelta(days=days)
            await db.execute("""
                INSERT INTO subscriptions (user_id, tariff, start_date, end_date, status)
                VALUES (?, ?, ?, ?, 'active')
            """, (user_id, tariff, start.isoformat(), end.isoformat()))

        await db.commit()


async def count_active_subscriptions() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT COUNT(*) FROM subscriptions
            WHERE status = 'active' AND end_date >= datetime('now')
        """) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def delete_subscription(user_id: int):
    """Foydalanuvchi obunasini o'chirish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE subscriptions SET status = 'expired' WHERE user_id = ? AND status = 'active'", (user_id,))
        await db.commit()


async def get_all_active_taxi_ids() -> list[int]:
    """Aktiv obunali barcha taxi haydovchilar ID lari"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT DISTINCT u.telegram_id FROM users u
            JOIN subscriptions s ON u.telegram_id = s.user_id
            WHERE u.role = 'taxi' AND s.status = 'active' AND s.end_date >= datetime('now')
        """) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


# ─── PAYMENTS ─────────────────────────────────────────────────────────────────

async def create_payment(user_id: int, tariff: str, amount: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO payments (user_id, tariff, amount, status)
            VALUES (?, ?, ?, 'pending')
        """, (user_id, tariff, amount))
        await db.commit()
        return cursor.lastrowid


async def get_payment(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM payments WHERE id = ?", (payment_id,)
        ) as cursor:
            return await cursor.fetchone()


async def update_payment_status(payment_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status = ? WHERE id = ?", (status, payment_id)
        )
        await db.commit()


async def count_payments() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM payments WHERE status = 'approved'") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ─── ANALYTICS & CANCELLATIONS ────────────────────────────────────────────────

async def log_analytics(event_name: str, user_id: int = None, order_id: int = None, meta: dict = None):
    """Analytics eventini bazaga yozish"""
    import json
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO analytics (event_name, user_id, order_id, meta)
            VALUES (?, ?, ?, ?)
        """, (event_name, user_id, order_id, json.dumps(meta) if meta else None))
        await db.commit()


async def log_cancellation(user_id: int, role: str, order_id: int, reason: str):
    """Bekor qilish sababini saqlash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO cancellations (user_id, role, order_id, reason)
            VALUES (?, ?, ?, ?)
        """, (user_id, role, order_id, reason))
        await db.commit()


# ─── DRIVER LOCATIONS ─────────────────────────────────────────────────────────

async def update_driver_location_db(user_id: int, lat: float, lon: float):
    """Haydovchi lokatsiyasini yangilash"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO driver_locations (user_id, latitude, longitude, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                updated_at = datetime('now')
        """, (user_id, lat, lon))
        await db.commit()


async def get_driver_location(user_id: int):
    """Haydovchi lokatsiyasini va yangilangan vaqtini olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT *, (strftime('%s', 'now') - strftime('%s', updated_at)) as age_sec FROM driver_locations WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            return await cursor.fetchone()


# ─── ORDERS ───────────────────────────────────────────────────────────────────

async def create_order(client_id, from_loc, to_loc, order_time, price, phone, lat, lon, passengers, gender, contact_phone, idempotency_key):
    """Yangi buyurtma yaratish (Idempotent)"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            async with db.execute("""
                INSERT INTO orders (client_id, from_loc, to_loc, order_time, price, phone, latitude, longitude, passengers, gender, contact_phone, idempotency_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (client_id, from_loc, to_loc, order_time, price, phone, lat, lon, passengers, gender, contact_phone, idempotency_key)) as cursor:
                order_id = cursor.lastrowid
                await db.commit()
                return order_id
        except aiosqlite.IntegrityError:
            # Idempotency key conflict - return existing order
            async with db.execute("SELECT id FROM orders WHERE idempotency_key = ?", (idempotency_key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None


async def get_order_by_idempotency_key(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE idempotency_key = ?", (key,)) as cursor:
            return await cursor.fetchone()


async def increment_rebroadcast_count(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET rebroadcast_count = rebroadcast_count + 1 WHERE id = ?", (order_id,))
        await db.commit()


async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            return await cursor.fetchone()


async def take_order(order_id: int, taxi_id: int) -> bool:
    """Buyurtmani olish — faqat birinchi bosgan oladi (atomik)"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE orders SET status = 'taken', taken_by = ?
            WHERE id = ? AND status = 'pending'
        """, (taxi_id, order_id))
        await db.commit()
        return cursor.rowcount > 0  # True = muvaffaqiyatli olindi


async def expire_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET status = 'expired'
            WHERE id = ? AND status = 'pending'
        """, (order_id,))
        await db.commit()


async def cancel_order_db(order_id: int, role: str, reason: str):
    """Buyurtmani bekor qilish"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET status = 'cancelled', cancel_by = ?, cancel_reason = ?
            WHERE id = ?
        """, (role, reason, order_id))
        await db.commit()


async def reset_order_to_pending(order_id: int):
    """Buyurtmani qayta ochiq holatga keltirish (agar haydovchi bekor qilsa)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders SET status = 'pending', taken_by = NULL
            WHERE id = ?
        """, (order_id,))
        await db.commit()

async def get_client_orders(client_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE client_id = ? ORDER BY created_at DESC LIMIT 20", (client_id,)
        ) as cursor:
            return await cursor.fetchall()

async def get_taxi_orders(taxi_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE taken_by = ? ORDER BY created_at DESC LIMIT 20", (taxi_id,)
        ) as cursor:
            return await cursor.fetchall()

async def get_all_orders(limit: int = 50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            return await cursor.fetchall()

# ─── TARIFFS ──────────────────────────────────────────────────────────────────

async def get_tariffs():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tariffs ORDER BY price ASC") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                # Agar jadval bo'sh bo'lsa defaultlarni qo'shib qo'yamiz
                await db.executemany(
                    "INSERT INTO tariffs (key, name, price, days) VALUES (?, ?, ?, ?)",
                    [
                        ("day", "⚡ 1 kun (Sinab ko'rish)", 15000, 1),
                        ("week", "⚡ 1 hafta (Qisqa muddatli)", 50000, 7),
                        ("month", "⭐ 1 oy (ENG OMMABOP)", 99000, 30),
                        ("3month", "🚀 3 oy (Eng foydali -30%)", 210000, 90),
                        ("6month", "💼 6 oy (Arzonroq)", 380000, 180),
                        ("year", "👑 1 yil (Best deal -40%)", 700000, 365),
                    ]
                )
                await db.commit()
                async with db.execute("SELECT * FROM tariffs ORDER BY price ASC") as cur2:
                    rows = await cur2.fetchall()
            return rows

async def update_tariff(key: str, price: int, days: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tariffs SET price = ?, days = ? WHERE key = ?", (price, days, key))
        await db.commit()


async def count_orders() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_stats_by_period(days: int):
    """Ma'lum kunlik statistikani qaytaradi"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Yangi foydalanuvchilar
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', ?)", (f'-{days} days',)
        ) as cursor:
            new_users = (await cursor.fetchone())[0]

        # Yangi buyurtmalar
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at >= datetime('now', ?)", (f'-{days} days',)
        ) as cursor:
            new_orders = (await cursor.fetchone())[0]

        # Tasdiqlangan to'lovlar va ularning summasi
        async with db.execute("""
            SELECT COUNT(*), SUM(amount) FROM payments 
            WHERE status = 'approved' AND created_at >= datetime('now', ?)
        """, (f'-{days} days',)) as cursor:
            res = await cursor.fetchone()
            payment_count = res[0]
            payment_sum = res[1] or 0

        return {
            "new_users": new_users,
            "new_orders": new_orders,
            "payment_count": payment_count,
            "payment_sum": payment_sum
        }
