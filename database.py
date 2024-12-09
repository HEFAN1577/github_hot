import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('github_trending.db')
    c = conn.cursor()
    
    # 创建仓库表（不删除已有数据）
    c.execute('''
        CREATE TABLE IF NOT EXISTS repos
        (name TEXT PRIMARY KEY,
         url TEXT,
         description TEXT,
         stars INTEGER,
         created_at TEXT,
         updated_at TEXT,
         language TEXT,
         topics TEXT,
         star_growth FLOAT,
         forks INTEGER,
         fetch_time TEXT
        )
    ''')
    
    # 创建更新记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS update_history
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         update_time TEXT,
         repos_count INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

def insert_repos(repos):
    conn = sqlite3.connect('github_trending.db')
    c = conn.cursor()
    
    fetch_time = datetime.now().isoformat()
    
    for repo in repos:
        language = repo.get('language') or ''
        topics = ','.join(repo.get('topics', []))
        
        c.execute('''
            INSERT OR REPLACE INTO repos
            (name, url, description, stars, created_at, updated_at, 
             language, topics, star_growth, forks, fetch_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            repo['name'],
            repo['url'],
            repo['description'],
            repo['stars'],
            repo['created_at'],
            repo['updated_at'],
            language,
            topics,
            repo['star_growth'],
            repo['forks'],
            fetch_time
        ))
    
    # 记录更新历史
    c.execute('''
        INSERT INTO update_history (update_time, repos_count)
        VALUES (?, ?)
    ''', (fetch_time, len(repos)))
    
    conn.commit()
    conn.close()

def get_repos(language=None, page=1, per_page=12, date=None):
    conn = sqlite3.connect('github_trending.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    try:
        # 基础查询
        base_query = 'SELECT * FROM repos'
        count_query = 'SELECT COUNT(*) FROM repos'
        conditions = []
        params = []
        
        # 语言筛选
        if language and language != 'all':
            conditions.append('LOWER(language) = LOWER(?)')
            params.append(language)
        else:
            conditions.append('LOWER(language) IN (?, ?)')
            params.extend(['python', 'javascript'])
        
        # 日期筛选
        if date:
            conditions.append("DATE(fetch_time) = DATE(?)")
            params.append(date)
        
        # 添加 WHERE 子句
        if conditions:
            where_clause = ' WHERE ' + ' AND '.join(conditions)
            base_query += where_clause
            count_query += where_clause
        
        # 获取总记录数
        c.execute(count_query, params)
        total_count = c.fetchone()[0]
        
        # 计算总页数
        total_pages = max((total_count + per_page - 1) // per_page, 1)
        
        # 确保页码在有效范围内
        page = max(1, min(page, total_pages))
        
        # 添加排序和分页
        base_query += ' ORDER BY CAST(stars AS INTEGER) DESC'
        offset = (page - 1) * per_page
        base_query += f' LIMIT {per_page} OFFSET {offset}'
        
        # 执行查询
        c.execute(base_query, params)
        repos = c.fetchall()
        
        print(f"Page {page}/{total_pages}, showing {len(repos)} of {total_count} repositories")
        
        return {
            'repos': repos,
            'total_pages': total_pages,
            'current_page': page,
            'total_count': total_count
        }
        
    except Exception as e:
        print(f"Database error: {e}")
        return {
            'repos': [],
            'total_pages': 1,
            'current_page': 1,
            'total_count': 0
        }
    finally:
        conn.close()

def get_last_update_time():
    conn = sqlite3.connect('github_trending.db')
    c = conn.cursor()
    
    try:
        c.execute('SELECT update_time FROM update_history ORDER BY id DESC LIMIT 1')
        result = c.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def get_available_dates():
    """获取所有可用的数据日期"""
    conn = sqlite3.connect('github_trending.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT DISTINCT DATE(fetch_time) as date 
            FROM repos 
            ORDER BY date DESC
        ''')
        dates = [row[0] for row in c.fetchall()]
        return dates
    finally:
        conn.close()

def cleanup_old_data():
    """清理30天前的数据"""
    conn = sqlite3.connect('github_trending.db')
    c = conn.cursor()
    
    try:
        # 计算30天前的日期
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # 删除30天前的仓库数据
        c.execute('''
            DELETE FROM repos 
            WHERE DATE(fetch_time) < DATE(?)
        ''', (thirty_days_ago,))
        
        # 删除30天前的更新历史
        c.execute('''
            DELETE FROM update_history 
            WHERE DATE(update_time) < DATE(?)
        ''', (thirty_days_ago,))
        
        conn.commit()
        print(f"Cleaned up data older than {thirty_days_ago}")
    finally:
        conn.close() 