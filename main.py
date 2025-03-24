from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from typing import Annotated, List, Union

import boto3
import json
import os
import psycopg2


AWS_SERVICE_NAME = os.getenv("AWS_SERVICE_NAME")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

MODEL_ID = os.getenv("MODEL_ID")
MAX_LENGTH = int(os.getenv("MAX_LENGTH"))
TEMPERATURE = float(os.getenv("TEMPERATURE"))
TOP_P = float(os.getenv("TOP_P"))

with open("system_prompt.txt", "r") as file:
    SYSTEM_PROMPT = file.read()

DATABASE_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "sslmode": os.getenv("DB_SSL"),
}

STORAGE_FOLDER = "reports"


llm_model_client = boto3.client(
    AWS_SERVICE_NAME,
    region_name=AWS_REGION_NAME,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
app = FastAPI()
app.mount(f"/{STORAGE_FOLDER}", StaticFiles(directory=STORAGE_FOLDER))
templates = Jinja2Templates(directory="./templates/")

class VacationPlanning(BaseModel):
    name: str
    group_size: int
    start_date: str
    end_date: str
    vacation_type: List[str]
    climate_preference: str
    goals: str
    activities: List[str]
    budget_range: int
    special_needs: Union[str, None]
    additional_info: Union[str, None]

def generate_prompt(user_prompt):
    system_section = f"<|start_header_id|>system<|end_header_id|>\n{SYSTEM_PROMPT}\n<|eot_id|>"
    user_section = f"<|start_header_id|>user<|end_header_id|>\n{user_prompt}\n<|eot_id|>"
    assistant_section = "<|start_header_id|>assistant<|end_header_id|>\n"
    prompt_text = "<|begin_of_text|>" + system_section + user_section + assistant_section
#     prompt_text = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
# {SYSTEM_PROMPT}
# <|eot_id|>
# <|start_header_id|>user<|end_header_id|>
# {user_section}
# <|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"""
    return prompt_text

def process_llm_query(prompt):
    body = json.dumps({
        "prompt": prompt,
        "max_gen_len": MAX_LENGTH,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
    })
    try:
        response = llm_model_client.invoke_model(modelId=MODEL_ID, body=body)
        generated_text = json.loads(response["body"].read().decode("utf-8"))["generation"]
        return generated_text
    except Exception as e:
        print("An error occurred:", e)
        return None

def perform_query(query: str, data = []):
    with psycopg2.connect(**DATABASE_CONFIG) as conn:
        with conn.cursor() as curr:
            curr.execute(query, data)
            output = curr.fetchall()
            return output

def generate_report(report_id, user_data: VacationPlanning):
    filename = f"report_{report_id}.pdf"
    c = canvas.Canvas(f"./{STORAGE_FOLDER}/{filename}", pagesize=A4)

    pdfmetrics.registerFont(TTFont("Arial", "./static/fonts/Arial.ttf"))

    c.setFont("Arial", 18)
    c.setFillColor(colors.blue)
    c.drawString(150, 750, f"Звіт по плануванню відпустки №{report_id}")

    c.setStrokeColor(colors.black)
    c.line(30, 745, 580, 745)

    c.setFont("Arial", 12)
    y_position = 700

    def draw_text(label, value):
        nonlocal y_position
        c.setFillColor(colors.black)
        c.drawString(30, y_position, label)
        c.drawString(250, y_position, value)
        y_position -= 20

    data = {
        "Ім'я": user_data.name,
        "Кількість людей": str(user_data.group_size),
        "Дата початку": user_data.start_date,
        "Дата закінчення": user_data.end_date,
        "Тип відпочинку": ",".join(user_data.vacation_type),
        "Кліматичні уподобання": user_data.climate_preference,
        "Цілі": user_data.goals,
        "Активності": ",".join(user_data.activities),
        "Бюджет": str(user_data.budget_range),
        "Особливі потреби": user_data.special_needs,
        "Додаткова інформація": user_data.additional_info
    }

    for key, value in data.items():
        draw_text(key + ":", value)

    c.showPage()
    c.save()
    return filename


@app.get("/", response_class=HTMLResponse)
def get_index(request: Request, created_report_id=None):
    select_query = """SELECT id, name, created_at from vacation_planning ORDER BY created_at DESC"""
    result = perform_query(select_query)
    data = [{"report_id": i[0], "name": i[1], "created_at": i[2], "last_created": created_report_id==str(i[0])} for i in result]
    return templates.TemplateResponse("index.html", {"request": request, "data": data})

    
@app.get("/form", response_class=HTMLResponse)
def get_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.get("/ask")
def ask(message: str):
    prompt = generate_prompt(message)
    generated_text = process_llm_query(prompt)
    print(generated_text)
    return json.loads(generated_text)


@app.post("/submit")
def submit_form(
    request: Request,
    data: Annotated[VacationPlanning, Form()]
):
    insert_query = """
        INSERT INTO vacation_planning (
            name, group_size, start_date, end_date, vacation_type, 
            climate_preference, goals, activities, budget_range, special_needs, additional_info
        ) VALUES %s RETURNING id
    """
    input_data = [(
        data.name, data.group_size, data.start_date, data.end_date, data.vacation_type,
        data.climate_preference, data.goals, data.activities, data.budget_range,
        data.special_needs, data.additional_info
    )]
    result = perform_query(insert_query, input_data)
    record_id = result[0][0]
    generate_report(record_id, data)

    redirect_url = request.url_for("get_index").include_query_params(created_report_id=f"{record_id}")
    return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)

