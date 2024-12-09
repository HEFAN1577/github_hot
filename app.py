from flask import Flask, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from crawler import fetch_trending_repos
from database import init_db, get_repos, get_last_update_time, get_available_dates, cleanup_old_data
import atexit
import os

app = Flask(__name__)

# 初始化数据库
init_db()

def scheduled_job():
    """定时任务：抓取数据并清理旧数据"""
    fetch_trending_repos(per_page=100)  # 指定每次抓取100个项目
    cleanup_old_data()

# 创建定时任务，设置为每天凌晨2点执行
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=scheduled_job,
    trigger=CronTrigger(hour=2),  # 每天凌晨2点执行
    id='daily_fetch',
    name='Fetch daily trending repos'
)
scheduler.start()

# 确保程序退出时关闭定时任务
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    try:
        language = request.args.get('language', 'all')
        page = max(1, int(request.args.get('page', 1)))
        date = request.args.get('date')
        
        # 获取所有可用日期
        available_dates = get_available_dates()
        
        # 获取仓库数据
        result = get_repos(
            language=language,
            page=page,
            per_page=12,
            date=date,
        )
        
        # 获取最后更新时间
        last_update = get_last_update_time()
        
        # 获取所有可用的主题
        topics = set()
        for repo in result['repos']:
            if repo['topics']:
                topics.update(repo['topics'].split(','))
        
        return render_template('index.html', 
                             repos=result['repos'],
                             current_language=language,
                             current_date=date,
                             available_dates=available_dates,
                             topics=sorted(topics),
                             pagination=result,
                             last_update=last_update)
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index.html',
                             repos=[],
                             current_language='all',
                             current_date=None,
                             available_dates=[],
                             topics=[],
                             pagination={'current_page': 1, 'total_pages': 1, 'total_count': 0},
                             last_update=None)

if __name__ == '__main__':
    # 第一次运行时获取数据
    print("Fetching initial data...")
    scheduled_job()  # 使用新的scheduled_job函数
    app.run(debug=True) 