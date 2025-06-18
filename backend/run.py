import uvicorn
print("🚀 מריץ main מתוך backend")

if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
