from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
from main import Config, ManualSearchSystem
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FAISS Manual Search API")

# 启用 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化搜索系统
config = Config()
system = ManualSearchSystem(config)
system.initialize()
system.load_existing_index()

class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = 5

class SearchResult(BaseModel):
    rank: int
    similarity_score: float
    file_path: str
    file_name: str
    content: str

@app.get("/")
def read_root():
    return {"status": "ok", "message": "FAISS Manual Search API is running"}

@app.post("/search", response_model=List[SearchResult])
async def search(query_data: SearchQuery):
    if not system.faiss_index.index:
        raise HTTPException(status_code=400, detail="Index not built or loaded")
    
    try:
        results = system.search(query_data.query, query_data.top_k)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rebuild")
async def rebuild_index():
    try:
        system.build_index_from_directory()
        return {"message": "Index rebuilt successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update")
async def update_index():
    try:
        system.update_index_from_directory()
        return {"message": "Index updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/readme")
async def get_readme():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        readme_path = os.path.join(current_dir, "README.md")
        
        print(f"Attempting to read README at: {readme_path}") # Debug log
        
        if not os.path.exists(readme_path):
            print(f"README file not found at: {readme_path}")
            raise HTTPException(status_code=404, detail=f"README.md not found at {readme_path}")
            
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error reading README: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 确保 data 目录存在
        data_path = system.config.DATA_DIR
        os.makedirs(data_path, exist_ok=True)

        # 保存上传的文件
        file_location = os.path.join(data_path, file.filename)
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        # 更新索引
        system.update_index_from_directory()
        
        return {"message": f"文件 '{file.filename}' 上传成功并已加入索引。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传或索引更新失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
