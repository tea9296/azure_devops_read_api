# Azure DevOps API - 使用指南

## 🔐 安全設計

此 API **不儲存任何 PAT**，每個使用者使用自己的 Azure DevOps Personal Access Token 來呼叫。

---

## 📝 如何取得 PAT

1. 到 Azure DevOps → 右上角頭像 → Personal Access Tokens
2. 點擊 "New Token"
3. 設定權限：
   - **Work Items**: Read
   - **Project and Team**: Read
4. 複製生成的 Token（只會顯示一次！）

---

## 🚀 如何使用 API

### 基本格式

所有請求都需要在 header 中包含你的 PAT：

```bash
Authorization: Bearer YOUR_AZURE_DEVOPS_PAT
```

### 範例 1: 列出所有 Sprints

```bash
curl -H "Authorization: Bearer YOUR_PAT" \
  https://your-api-url.vercel.app/sprints
```


### 範例 2: 查詢 Sprint 37 的工作項目

```bash
curl -H "Authorization: Bearer YOUR_PAT" \
  "https://your-api-url.vercel.app/work-items?sprint=Sprint%2037"
```

### 範例 3: 取得簡化摘要（適合 LLM）

```bash
curl -H "Authorization: Bearer YOUR_PAT" \
  "https://your-api-url.vercel.app/work-items/summary?sprint=Sprint%2037"
```

---

## 🔧 在程式中使用

### Python

```python
import requests

PAT = "your_pat_here"
API_URL = "https://your-api-url.vercel.app"

headers = {
    "Authorization": f"Bearer {PAT}"
}

# 列出 Sprints
response = requests.get(f"{API_URL}/sprints", headers=headers)
sprints = response.json()

# 查詢工作項目
response = requests.get(
    f"{API_URL}/work-items/summary",
    params={"sprint": "Sprint 37"},
    headers=headers
)
items = response.json()
```

### JavaScript

```javascript
const PAT = 'your_pat_here';
const API_URL = 'https://your-api-url.vercel.app';

const headers = {
  'Authorization': `Bearer ${PAT}`
};

// 列出 Sprints
fetch(`${API_URL}/sprints`, { headers })
  .then(res => res.json())
  .then(data => console.log(data));

// 查詢工作項目
fetch(`${API_URL}/work-items/summary?sprint=Sprint%2037`, { headers })
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 📚 API 端點

| 端點 | 說明 | 需要 Auth |
|-----|------|----------|
| `GET /` | API 說明 | ❌ |
| `GET /health` | 健康檢查 | ❌ |
| `GET /sprints` | 列出所有 Sprints | ✅ |
| `GET /work-items?sprint=Sprint 37` | 查詢完整工作項目 | ✅ |
| `GET /work-items/summary?sprint=Sprint 37` | 查詢簡化摘要 | ✅ |

---

## 🔒 安全注意事項

### ✅ 好的做法
- 每個人使用自己的 PAT
- PAT 只給最小必要權限（Work Items: Read）
- 定期更換 PAT
- 不要在程式碼中硬寫 PAT

### ❌ 不要做
- 不要分享你的 PAT 給別人
- 不要把 PAT 提交到 Git
- 不要給 PAT 過多權限

---

## 💡 給團隊成員的說明

分享這個訊息給你的團隊：

> **Azure DevOps API 使用說明**
> 
> API URL: `https://your-api-url.vercel.app`
> 
> **如何使用：**
> 1. 到 Azure DevOps 建立你自己的 Personal Access Token（權限：Work Items Read）
> 2. 使用時在 header 加上：`Authorization: Bearer YOUR_PAT`
> 3. 查看完整 API 文件：`https://your-api-url.vercel.app/docs`
> 
> **範例：**
> ```bash
> curl -H "Authorization: Bearer YOUR_PAT" \
>   "https://your-api-url.vercel.app/work-items/summary?sprint=Sprint%2037"
> ```

---

## 🐛 錯誤處理

### 401 Unauthorized
- 檢查是否有提供 Authorization header
- 檢查 PAT 是否正確
- 檢查 PAT 是否過期

### 403 Forbidden
- PAT 權限不足
- 需要 Work Items: Read 權限

### 500 Server Error
- 聯絡管理員（可能是 AZURE_ORG 或 AZURE_PROJECT 設定錯誤）

