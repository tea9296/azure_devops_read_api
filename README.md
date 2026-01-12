# Azure DevOps Work Items API

查詢指定 Sprint 的 Azure DevOps work items，使用各自的 PAT 存取。

## ✨ 功能特色

- 🔍 **以 Sprint 為單位查詢** - 查詢指定 Sprint 中我建立的或指派給我的 work items
- 🔐 **安全設計** - 每個使用者使用自己的 PAT，不共用憑證
- 📊 **完整資訊** - 包含標題、描述、留言、狀態等詳細資訊
- 🤖 **LLM 友善** - 提供簡化摘要格式，適合 AI 處理
- 🌐 **部署簡單** - 支援 Vercel 一鍵部署
- 📚 **互動式文件** - 內建 Swagger UI

## 🚀 快速開始

### 部署到 Vercel

1. **Fork 此專案** 到你的 GitHub
2. 到 [Vercel](https://vercel.com) 註冊並 Import 此專案
3. **設定環境變數**：
   - `AZURE_ORG` - 你的 Azure DevOps 組織名稱
   - `AZURE_PROJECT` - 專案名稱
   - `AZURE_TEAM` - Team 名稱（可選）
4. **Deploy** 完成！

### 本地開發

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入 AZURE_ORG 和 AZURE_PROJECT

# 3. 啟動 API
uvicorn azu_api:app --reload --port 8001

# 4. 訪問 API 文件
# http://localhost:8001/docs
```

## 📖 API 端點

### 需要驗證的端點

所有端點（除了 `/` 和 `/health`）都需要在 header 中提供：

```
Authorization: Bearer YOUR_AZURE_DEVOPS_PAT
```

### `GET /sprints`
列出所有可用的 Sprints

**範例：**
```bash
curl -H "Authorization: Bearer YOUR_PAT" \
  https://your-api.vercel.app/sprints
```

### `GET /work-items?sprint=Sprint 37`
查詢指定 Sprint 的完整 work items

**參數：**
- `sprint` (必填): Sprint 名稱，例如 "Sprint 37"

**範例：**
```bash
curl -H "Authorization: Bearer YOUR_PAT" \
  "https://your-api.vercel.app/work-items?sprint=Sprint%2037"
```

### `GET /work-items/summary?sprint=Sprint 37`
取得簡化摘要（只有 title、description、comments）

**範例：**
```bash
curl -H "Authorization: Bearer YOUR_PAT" \
  "https://your-api.vercel.app/work-items/summary?sprint=Sprint%2037"
```

**回傳格式：**
```json
{
  "sprint": "Sprint 37",
  "total_count": 3,
  "items": [
    {
      "title": "實作登入功能",
      "description": "完整的描述內容...",
      "comments": ["留言1", "留言2"]
    }
  ]
}
```

### `GET /health`
健康檢查（不需要驗證）

## 🔐 如何取得 PAT

1. 到 Azure DevOps → 右上角頭像 → **Personal Access Tokens**
2. 點擊 **New Token**
3. 設定權限：
   - **Work Items**: Read
   - **Project and Team**: Read
4. 複製生成的 Token

## 💡 使用範例

### Python

```python
import requests

PAT = "your_pat_here"
API_URL = "https://your-api.vercel.app"

headers = {"Authorization": f"Bearer {PAT}"}

# 查詢 Sprint 37
response = requests.get(
    f"{API_URL}/work-items/summary",
    params={"sprint": "Sprint 37"},
    headers=headers
)

data = response.json()
for item in data['items']:
    print(f"• {item['title']}")
    if item.get('description'):
        print(f"  描述: {item['description'][:100]}...")
```

### JavaScript

```javascript
const PAT = 'your_pat_here';
const API_URL = 'https://your-api.vercel.app';

fetch(`${API_URL}/work-items/summary?sprint=Sprint%2037`, {
  headers: { 'Authorization': `Bearer ${PAT}` }
})
  .then(res => res.json())
  .then(data => console.log(data));
```

### cURL

```bash
curl -H "Authorization: Bearer YOUR_PAT" \
  "https://your-api.vercel.app/work-items/summary?sprint=Sprint%2037" \
  | jq '.items[] | .title'
```

## 🤖 LLM 整合

```python
import requests
import openai

# 1. 取得 work items
response = requests.get(
    "https://your-api.vercel.app/work-items/summary?sprint=Sprint%2037",
    headers={"Authorization": f"Bearer {PAT}"}
)
data = response.json()

# 2. 傳給 LLM 產生報告
prompt = f"""
根據以下 Sprint 37 的工作項目，產生一份簡潔的 Sprint 總結：

{data['items']}

請以條列式呈現主要工作內容。
"""

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)

print(response.choices[0].message.content)
```

## 🔧 環境變數

### 部署時需要設定（Vercel）

| 變數名稱 | 說明 | 必填 |
|---------|------|-----|
| `AZURE_ORG` | Azure DevOps 組織名稱 | ✅ |
| `AZURE_PROJECT` | 專案名稱 | ✅ |
| `AZURE_TEAM` | Team 名稱 | ❌ |

### 使用者需要自己的

| 變數名稱 | 說明 |
|---------|------|
| PAT (Personal Access Token) | 每次呼叫 API 時在 Authorization header 中提供 |

## 🛡️ 安全性

- ✅ API 不儲存任何 PAT
- ✅ 每個使用者使用自己的憑證
- ✅ HTTPS 加密傳輸
- ✅ 可追蹤個別使用者的操作

## 📚 相關文件

- [VERCEL_DEPLOY.md](VERCEL_DEPLOY.md) - 詳細部署指南
- [USAGE.md](USAGE.md) - 完整使用說明與團隊分享指南
- [Swagger UI](https://your-api.vercel.app/docs) - 互動式 API 文件

## 🐛 常見問題

### 401 Unauthorized
- 檢查 Authorization header 格式是否正確
- 確認 PAT 是否有效
- 確認 PAT 權限是否足夠

### 找不到 work items
- 確認 Sprint 名稱是否正確（區分大小寫）
- 檢查你在該 Sprint 是否有建立或被指派的 work items

### 部署失敗
- 確認 Python 版本為 3.12
- 檢查 Vercel 環境變數是否設定正確

## 📄 授權

MIT License
