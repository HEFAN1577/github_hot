import requests
from datetime import datetime, timedelta
from database import insert_repos
import time

def fetch_trending_repos(language='all', min_stars=10, category=None, days=7, per_page=100):
    """
    获取热门仓库
    language: 编程语言 (python, javascript, all)
    min_stars: 最小star数
    category: 项目类型/主题
    days: 统计的天数
    per_page: 每次抓取的项目数量
    """
    # 如果指定了语言，就分别获取
    if language == 'all':
        languages = ['python', 'javascript']
        # 平均分配每个语言的配额
        per_language = per_page // len(languages)
    else:
        languages = [language]
        per_language = per_page
    
    all_processed_repos = []
    
    for lang in languages:
        # 计算需要的页数
        pages = (per_language + 99) // 100  # 向上取整，因为GitHub API每页最多100个结果
        
        for page in range(1, pages + 1):
            # 计算当前页需要获取的数量
            current_page_size = min(100, per_language - len(all_processed_repos))
            if current_page_size <= 0:
                break
                
            processed_repos = fetch_repos_by_language(
                lang, 
                min_stars, 
                category, 
                days,
                current_page_size,
                page
            )
            
            if processed_repos:
                all_processed_repos.extend(processed_repos)
                print(f"Fetched {len(processed_repos)} {lang} repositories from page {page}")
                
            # 添加延时避免触发 API 限制
            time.sleep(2)
    
    if all_processed_repos:
        # 存入数据库
        insert_repos(all_processed_repos)
        print(f"Successfully processed total {len(all_processed_repos)} repositories")
    else:
        print("No repositories were processed")

def fetch_repos_by_language(language, min_stars, category, days, per_page=100, page=1):
    url = "https://api.github.com/search/repositories"
    
    # 计算指定天数前的日期
    days_ago = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # 构建查询条件
    query = f"language:{language} created:>{days_ago} stars:>={min_stars}"
    
    if category:
        query += f" topic:{category}"
    
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
        "page": page
    }
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        # 如果有 GitHub Token，请取消下面这行的注释并添加你的 token
        # "Authorization": "token YOUR_GITHUB_TOKEN"
    }
    
    try:
        print(f"Fetching {language} repositories with query: {query}")
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if "items" not in data:
            print(f"Error: No 'items' in response for {language}: {data}")
            return []
            
        repos = data["items"]
        print(f"Found {len(repos)} {language} repositories")
        
        processed_repos = []
        for repo in repos:
            try:
                # 确保数值类型正确
                stars = int(repo['stargazers_count'])
                forks = int(repo['forks_count'])
                
                repo_info = {
                    'name': repo['full_name'],
                    'url': repo['html_url'],
                    'description': repo['description'] or '',
                    'stars': stars,  # 确保是整数
                    'created_at': repo['created_at'],
                    'updated_at': datetime.now().isoformat(),
                    'language': repo['language'] or '',
                    'topics': repo.get('topics', []),
                    'star_growth': stars,  # 使用整数
                    'forks': forks  # 确保是整数
                }
                processed_repos.append(repo_info)
                print(f"Processing repo {repo_info['name']} with {stars} stars")  # 调试信息
                
            except Exception as e:
                print(f"Error processing repo {repo.get('full_name', 'unknown')}: {e}")
                continue
        
        # 在返回之前按 stars 排序
        processed_repos.sort(key=lambda x: x['stars'], reverse=True)
        return processed_repos
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {language} data from GitHub API: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error while fetching {language} repos: {e}")
        return []

if __name__ == "__main__":
    # 测试函数
    fetch_trending_repos()