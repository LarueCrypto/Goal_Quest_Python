import sqlite3
import json
from datetime import datetime, date
import pytz

class Database:
    def __init__(self, db_name="goal_quest.db"):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # User profile table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                name TEXT DEFAULT 'Adventurer',
                level INTEGER DEFAULT 1,
                current_xp INTEGER DEFAULT 0,
                total_xp INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                strength INTEGER DEFAULT 10,
                intelligence INTEGER DEFAULT 10,
                vitality INTEGER DEFAULT 10,
                agility INTEGER DEFAULT 10,
                sense INTEGER DEFAULT 10,
                luck INTEGER DEFAULT 10,
                rank_title TEXT DEFAULT 'Beginner',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Habits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                difficulty INTEGER DEFAULT 2,
                xp_reward INTEGER DEFAULT 200,
                category TEXT DEFAULT 'health',
                color TEXT DEFAULT 'blue',
                is_priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0
            )
        ''')
        
        # Habit completions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS habit_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER,
                completion_date DATE,
                xp_earned INTEGER,
                FOREIGN KEY (habit_id) REFERENCES habits(id),
                UNIQUE(habit_id, completion_date)
            )
        ''')
        
        # Goals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                difficulty INTEGER DEFAULT 1,
                xp_reward INTEGER DEFAULT 1000,
                deadline DATE,
                progress INTEGER DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                is_priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                deleted INTEGER DEFAULT 0
            )
        ''')
        
        # Goal steps table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goal_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER,
                step_text TEXT,
                is_completed INTEGER DEFAULT 0,
                suggested_habit TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            )
        ''')
        
        # Notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                category TEXT DEFAULT 'Personal',
                tags TEXT,
                ai_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0
            )
        ''')
        
        # Achievements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                xp_reward INTEGER,
                is_unlocked INTEGER DEFAULT 0,
                unlocked_at TIMESTAMP
            )
        ''')
        
        # Daily wisdom quotes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_quotes (
                id INTEGER PRIMARY KEY,
                quote_date DATE UNIQUE,
                quote_text TEXT,
                source TEXT
            )
        ''')
        
        conn.commit()
        
        # Initialize default user if not exists
        cursor.execute("SELECT COUNT(*) FROM user_profile")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO user_profile (id, name, level, current_xp, total_xp, gold)
                VALUES (1, 'Adventurer', 1, 0, 0, 0)
            ''')
        
        # Initialize achievements
        self._init_achievements(cursor)
        
        conn.commit()
        conn.close()
    
    def _init_achievements(self, cursor):
        achievements = [
            ("Habit Former", "Complete your first habit", 500),
            ("Week Warrior", "Maintain a 7-day streak", 1000),
            ("Monthly Master", "Maintain a 30-day streak", 2500),
            ("Rising Star", "Reach Level 5", 1000),
            ("Seasoned Adventurer", "Reach Level 10", 2000),
            ("Elite Champion", "Reach Level 25", 5000),
            ("Legendary Hero", "Reach Level 50", 10000),
            ("Goal Setter", "Complete your first goal", 750),
            ("Achiever", "Complete 5 goals", 1500),
            ("Habit Collector", "Create 10 habits", 1000),
            ("Perfect Day", "Complete all habits in a single day", 1500)
        ]
        
        for name, desc, xp in achievements:
            cursor.execute('''
                INSERT OR IGNORE INTO achievements (name, description, xp_reward)
                VALUES (?, ?, ?)
            ''', (name, desc, xp))
    
    def get_user_profile(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profile WHERE id = 1")
        profile = dict(cursor.fetchone())
        conn.close()
        return profile
    
    def update_user_profile(self, **kwargs):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        
        cursor.execute(f"UPDATE user_profile SET {fields} WHERE id = 1", values)
        conn.commit()
        conn.close()
    
    def add_xp(self, xp_amount):
        profile = self.get_user_profile()
        new_total_xp = profile['total_xp'] + xp_amount
        new_current_xp = profile['current_xp'] + xp_amount
        
        # Calculate level (500 XP increment per level)
        new_level = 1
        xp_for_level = new_total_xp
        
        while xp_for_level >= (new_level * 500):
            xp_for_level -= (new_level * 500)
            new_level += 1
        
        new_level = min(new_level, 100)
        
        # Update rank title
        rank_titles = {
            1: "Beginner", 5: "Apprentice", 10: "Adventurer",
            15: "Warrior", 20: "Expert", 25: "Elite",
            30: "Master", 40: "Champion", 50: "Legend",
            75: "Mythic", 100: "Transcendent"
        }
        
        rank_title = "Beginner"
        for level_threshold in sorted(rank_titles.keys(), reverse=True):
            if new_level >= level_threshold:
                rank_title = rank_titles[level_threshold]
                break
        
        self.update_user_profile(
            total_xp=new_total_xp,
            current_xp=xp_for_level,
            level=new_level,
            rank_title=rank_title
        )
        
        return new_level, xp_amount
    
    def create_habit(self, name, difficulty, xp_reward, category='health', color='blue'):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO habits (name, difficulty, xp_reward, category, color)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, difficulty, xp_reward, category, color))
        conn.commit()
        habit_id = cursor.lastrowid
        conn.close()
        return habit_id
    
    def get_habits(self, include_deleted=False):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM habits"
        if not include_deleted:
            query += " WHERE deleted = 0"
        query += " ORDER BY is_priority DESC, created_at DESC"
        
        cursor.execute(query)
        habits = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return habits
    
    def update_habit(self, habit_id, **kwargs):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [habit_id]
        
        cursor.execute(f"UPDATE habits SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
    
    def delete_habit(self, habit_id):
        self.update_habit(habit_id, deleted=1)
    
    def complete_habit(self, habit_id, completion_date=None):
        if completion_date is None:
            cst = pytz.timezone('America/Chicago')
            completion_date = datetime.now(cst).date()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT xp_reward FROM habits WHERE id = ?", (habit_id,))
        habit = cursor.fetchone()
        
        if not habit:
            conn.close()
            return False
        
        xp_earned = habit['xp_reward']
        
        cursor.execute('''
            SELECT id FROM habit_completions
            WHERE habit_id = ? AND completion_date = ?
        ''', (habit_id, completion_date))
        
        if cursor.fetchone():
            conn.close()
            return False
        
        cursor.execute('''
            INSERT INTO habit_completions (habit_id, completion_date, xp_earned)
            VALUES (?, ?, ?)
        ''', (habit_id, completion_date, xp_earned))
        
        conn.commit()
        conn.close()
        
        self.add_xp(xp_earned)
        
        return True
    
    def get_habit_completions(self, habit_id=None, start_date=None, end_date=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM habit_completions WHERE 1=1"
        params = []
        
        if habit_id:
            query += " AND habit_id = ?"
            params.append(habit_id)
        
        if start_date:
            query += " AND completion_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND completion_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY completion_date DESC"
        
        cursor.execute(query, params)
        completions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return completions
    
    def create_goal(self, title, description, difficulty, xp_reward, deadline=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO goals (title, description, difficulty, xp_reward, deadline)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, description, difficulty, xp_reward, deadline))
        conn.commit()
        goal_id = cursor.lastrowid
        conn.close()
        return goal_id
    
    def get_goals(self, include_completed=True, include_deleted=False):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM goals WHERE 1=1"
        
        if not include_completed:
            query += " AND is_completed = 0"
        
        if not include_deleted:
            query += " AND deleted = 0"
        
        query += " ORDER BY is_priority DESC, is_completed ASC, created_at DESC"
        
        cursor.execute(query)
        goals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return goals
    
    def update_goal(self, goal_id, **kwargs):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [goal_id]
        
        cursor.execute(f"UPDATE goals SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
    
    def complete_goal(self, goal_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT xp_reward FROM goals WHERE id = ?", (goal_id,))
        goal = cursor.fetchone()
        
        if goal:
            self.update_goal(goal_id, is_completed=1, progress=100, completed_at=datetime.now())
            self.add_xp(goal['xp_reward'])
            conn.close()
            return True
        
        conn.close()
        return False
    
    def create_note(self, title, content, category='Personal', tags=''):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notes (title, content, category, tags)
            VALUES (?, ?, ?, ?)
        ''', (title, content, category, tags))
        conn.commit()
        note_id = cursor.lastrowid
        conn.close()
        return note_id
    
    def get_notes(self, include_deleted=False):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM notes"
        if not include_deleted:
            query += " WHERE deleted = 0"
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query)
        notes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return notes
    
    def update_note(self, note_id, **kwargs):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        kwargs['updated_at'] = datetime.now()
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [note_id]
        
        cursor.execute(f"UPDATE notes SET {fields} WHERE id = ?", values)
        conn.commit()
        conn.close()
