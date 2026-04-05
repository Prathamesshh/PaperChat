from fastapi import FastAPI, UploadFile
import shutil

app = FastAPI()

@app.post("/upload")
async def upload_pdf(file: UploadFile):

    file_location = f"data/uploaded_papers/{file.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"message": "File uploaded successfully"}