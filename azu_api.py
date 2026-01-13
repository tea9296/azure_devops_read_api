from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import re

# 載入環境變數
load_dotenv()

app = FastAPI(
    title="Azure DevOps Work Items API",
    description="查詢指定 Sprint 的 Azure DevOps work items（需要使用者自己的 PAT）",
    version="2.0.0"
)

# 設定（不再從環境變數讀取 PAT）
ORG = os.getenv("AZURE_ORG")
PROJECT = os.getenv("AZURE_PROJECT")
TEAM = os.getenv("AZURE_TEAM", PROJECT)
TIMEZONE = ZoneInfo('Asia/Taipei')


class Comment(BaseModel):
    id: int
    text: str
    created_by: Optional[str] = None
    created_date: Optional[str] = None


class WorkItem(BaseModel):
    id: int
    title: str
    state: str
    type: str
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    created_date: Optional[str] = None
    changed_date: Optional[str] = None
    changed_by: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    iteration_path: Optional[str] = None
    comments_count: Optional[int] = None
    comments: Optional[List[Comment]] = None
    web_url: Optional[str] = None


class SprintWorkItemsResponse(BaseModel):
    sprint: str
    total_count: int
    created_by_me: int
    assigned_to_me: int
    work_items: List[WorkItem]


def strip_html(text: str) -> str:
    """移除 HTML 標籤"""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    return clean.strip()


def get_comments_for_item(item_id: int, pat: str) -> List[dict]:
    """取得 work item 的所有留言"""
    comments = []
    try:
        comments_url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/wit/workItems/{item_id}/comments?api-version=7.1-preview.3"
        response = requests.get(
            comments_url,
            auth=HTTPBasicAuth('', pat),
            timeout=10
        )
        if response.status_code == 200:
            for comment in response.json().get('comments', []):
                comments.append({
                    "id": comment.get('id'),
                    "text": strip_html(comment.get('text', '')),
                    "created_by": comment.get('createdBy', {}).get('displayName'),
                    "created_date": comment.get('createdDate')
                })
    except Exception:
        pass
    return comments


def get_work_items_by_sprint(sprint: str, pat: str) -> dict:
    """
    根據指定 Sprint 查詢 Azure DevOps work items
    
    Args:
        sprint: Sprint 名稱，例如 "Sprint 37"
        pat: 使用者的 Azure DevOps Personal Access Token
    
    Returns:
        包含 work items 的字典
    """
    if not all([ORG, PROJECT]):
        raise HTTPException(
            status_code=500,
            detail="Azure DevOps 設定不完整，請聯繫管理員"
        )
    
    if not pat:
        raise HTTPException(
            status_code=401,
            detail="缺少 Authorization header，請提供你的 Azure DevOps PAT"
        )
    
    try:
        # 使用 WIQL 查詢指定 Sprint 中我建立的或指派給我的 work items
        # IterationPath 需要使用 UNDER 運算符（包含子路徑）
        wiql_url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/wit/wiql?api-version=7.1"
        
        # 組合完整的 Iteration Path
        iteration_path = f"{PROJECT}\\{sprint}"
        
        query = {
            "query": (
                "SELECT [System.Id] "
                "FROM WorkItems "
                f"WHERE [System.IterationPath] UNDER '{iteration_path}' "
                "AND ([System.CreatedBy] = @Me OR [System.AssignedTo] = @Me) "
                "ORDER BY [System.ChangedDate] DESC"
            )
        }
        
        response = requests.post(
            wiql_url,
            json=query,
            auth=HTTPBasicAuth('', pat),
            timeout=15
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"WIQL 查詢失敗: {response.text}"
            )
        
        work_items_result = response.json().get('workItems', [])
        
        if not work_items_result:
            return {
                "sprint": sprint,
                "total_count": 0,
                "created_by_me": 0,
                "assigned_to_me": 0,
                "work_items": []
            }
        
        work_item_ids = [item['id'] for item in work_items_result]
        
        # 批次抓取 work items 細節（每次最多 200 個）
        all_items_data = []
        batch_size = 200
        
        for i in range(0, len(work_item_ids), batch_size):
            batch_ids = work_item_ids[i:i + batch_size]
            details_url = f"https://dev.azure.com/{ORG}/{PROJECT}/_apis/wit/workitems"
            params = {
                "ids": ",".join(map(str, batch_ids)),
                "$expand": "all",
                "api-version": "7.1"
            }
            
            details_response = requests.get(
                details_url,
                params=params,
                auth=HTTPBasicAuth('', pat),
                timeout=15
            )
            
            if details_response.status_code == 200:
                all_items_data.extend(details_response.json().get('value', []))
        
        # 整理數據
        work_items = []
        created_by_me_count = 0
        assigned_to_me_count = 0
        
        for item in all_items_data:
            fields = item.get('fields', {})
            item_id = item['id']
            
            # 建立 web URL
            web_url = f"https://dev.azure.com/{ORG}/{PROJECT}/_workitems/edit/{item_id}"
            
            # 取得留言
            comments_count = fields.get('System.CommentCount', 0)
            comments = get_comments_for_item(item_id, pat) if comments_count > 0 else []
            
            # 取得建立者和指派者資訊
            created_by = fields.get('System.CreatedBy', {}).get('displayName') if isinstance(fields.get('System.CreatedBy'), dict) else fields.get('System.CreatedBy')
            assigned_to = fields.get('System.AssignedTo', {}).get('displayName') if isinstance(fields.get('System.AssignedTo'), dict) else fields.get('System.AssignedTo')
            changed_by = fields.get('System.ChangedBy', {}).get('displayName') if isinstance(fields.get('System.ChangedBy'), dict) else fields.get('System.ChangedBy')
            
            # 計算統計
            # 注意：這裡無法精確判斷 @Me，但我們會在回傳時標註
            
            work_items.append({
                "id": item_id,
                "title": fields.get('System.Title', 'N/A'),
                "state": fields.get('System.State', 'N/A'),
                "type": fields.get('System.WorkItemType', 'N/A'),
                "assigned_to": assigned_to,
                "created_by": created_by,
                "created_date": fields.get('System.CreatedDate'),
                "changed_date": fields.get('System.ChangedDate'),
                "changed_by": changed_by,
                "description": strip_html(fields.get('System.Description', '')),
                "tags": fields.get('System.Tags'),
                "iteration_path": fields.get('System.IterationPath'),
                "comments_count": comments_count,
                "comments": comments if comments else None,
                "web_url": web_url
            })
        
        return {
            "sprint": sprint,
            "total_count": len(work_items),
            "created_by_me": created_by_me_count,
            "assigned_to_me": assigned_to_me_count,
            "work_items": work_items
        }
    
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Azure DevOps API 錯誤: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"伺服器錯誤: {str(e)}")


@app.get("/")
async def root():
    """API 根路徑"""
    return {
        "message": "Azure DevOps Work Items API (Sprint 版本)",
        "authentication": "所有端點需要在 header 中提供: Authorization: Bearer YOUR_AZURE_DEVOPS_PAT",
        "endpoints": {
            "/sprints": "列出可用的 Sprints",
            "/work-items?sprint=Sprint 37": "查詢指定 Sprint 的 work items",
            "/work-items/summary?sprint=Sprint 37": "取得 Sprint 的摘要",
            "/health": "健康檢查"
        },
        "example": "curl -H 'Authorization: Bearer YOUR_PAT' https://api-url/sprints"
    }


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "timestamp": datetime.now(TIMEZONE).isoformat()}


@app.get("/sprints")
async def list_sprints(authorization: Optional[str] = Header(None, description="Bearer YOUR_AZURE_DEVOPS_PAT")):
    """列出所有可用的 Sprints"""
    if not all([ORG, PROJECT]):
        raise HTTPException(
            status_code=500,
            detail="Azure DevOps 設定不完整，請聯繫管理員"
        )
    
    # 從 Authorization header 提取 PAT
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="需要 Authorization header. 使用格式: Authorization: Bearer YOUR_PAT"
        )
    
    pat = authorization.replace("Bearer ", "").strip()
    
    try:
        # 取得 iterations（sprints）
        iterations_url = f"https://dev.azure.com/{ORG}/{PROJECT}/{TEAM}/_apis/work/teamsettings/iterations?api-version=7.1"
        
        response = requests.get(
            iterations_url,
            auth=HTTPBasicAuth('', pat),
            timeout=10
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"無法取得 Sprints: {response.text}"
            )
        
        iterations = response.json().get('value', [])
        
        sprints = []
        for iteration in iterations:
            attributes = iteration.get('attributes', {})
            sprints.append({
                "name": iteration.get('name'),
                "path": iteration.get('path'),
                "start_date": attributes.get('startDate'),
                "finish_date": attributes.get('finishDate'),
                "time_frame": attributes.get('timeFrame')  # past, current, future
            })
        
        # 按照 timeFrame 排序：current > future > past
        order = {'current': 0, 'future': 1, 'past': 2}
        sprints.sort(key=lambda x: order.get(x.get('time_frame', 'past'), 3))
        
        return {
            "total": len(sprints),
            "sprints": sprints
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"錯誤: {str(e)}")


@app.get("/work-items")
async def get_work_items(
    sprint: str = Query(
        ...,
        description="Sprint 名稱，例如 'Sprint 37'",
        examples=["Sprint 37"]
    ),
    authorization: Optional[str] = Header(None, description="Bearer YOUR_AZURE_DEVOPS_PAT")
):
    """
    查詢指定 Sprint 中我建立的或指派給我的 work items
    
    - **sprint**: Sprint 名稱（必填）
    - **authorization**: Authorization header with Bearer token
    """
    # 從 Authorization header 提取 PAT
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="需要 Authorization header. 使用格式: Authorization: Bearer YOUR_PAT"
        )
    
    pat = authorization.replace("Bearer ", "").strip()
    result = get_work_items_by_sprint(sprint, pat)
    return JSONResponse(content=result)


@app.get("/work-items/summary")
async def get_work_items_summary(
    sprint: str = Query(
        ...,
        description="Sprint 名稱，例如 'Sprint 37'",
        examples=["Sprint 37"]
    ),
    authorization: Optional[str] = Header(None, description="Bearer YOUR_AZURE_DEVOPS_PAT")
):
    """
    取得指定 Sprint 的 work items 摘要（適合 LLM 使用）
    
    - **sprint**: Sprint 名稱（必填）
    - **authorization**: Authorization header with Bearer token
    """
    # 從 Authorization header 提取 PAT
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="需要 Authorization header. 使用格式: Authorization: Bearer YOUR_PAT"
        )
    
    pat = authorization.replace("Bearer ", "").strip()
    
    result = get_work_items_by_sprint(sprint, pat)
    
    # 整理成簡潔的格式：只有 title、description、comments
    summary_items = []
    
    for item in result['work_items']:
        summary_item = {
            "title": item['title']
        }
        
        # 只有 description 有內容時才加入
        if item.get('description') and item['description'].strip():
            summary_item["description"] = item['description']
        
        # 只有留言時才加入
        if item.get('comments') and len(item['comments']) > 0:
            summary_item["comments"] = [c.get('text', '') for c in item['comments'] if c.get('text')]
        
        summary_items.append(summary_item)
    
    return {
        "sprint": result['sprint'],
        "total_count": result['total_count'],
        "items": summary_items
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
