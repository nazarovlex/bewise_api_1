from fastapi import FastAPI
from sqlalchemy import func, insert
from models import QuestionsTable, QuestionRequest
from database import database, engine, Base, SessionLocal
import requests
import uvicorn
from sqlalchemy.dialects.postgresql import insert


class ResponseError(Exception):
    pass


# FastAPI init
app = FastAPI()


# create all tables in DB
async def create_tables():
    # create table if not exist
    Base.metadata.create_all(bind=engine)


# connect to DB when app is start running
@app.on_event("startup")
async def startup():
    await database.connect()
    await create_tables()


# disconnect to DB when app is stopping
@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


# receiving questions from a third-party API
def get_questions(count: int) -> dict:
    url = "https://jservice.io/api/random?count="
    response = requests.get(url=url + str(count))
    if response.status_code != 200:
        raise ResponseError(f"jservice response error, status code: {response.status_code}")
    return response.json()


# try to insert question to DB
def insert_question(db_question: dict, session: SessionLocal()) -> SessionLocal():
    query = insert(QuestionsTable).values(**db_question).on_conflict_do_nothing(
        index_elements=[QuestionsTable.question_id])
    return session.execute(query)


@app.post("/questions")
async def questions(req_question: QuestionRequest) -> dict:
    session = SessionLocal()

    # get last question data
    last_record = session.query(QuestionsTable).filter(
        QuestionsTable.id == session.query(func.max(QuestionsTable.id)).scalar_subquery()).first()

    if last_record:
        last_record = {
            "question_id": last_record.question_id,
            "question_text": last_record.question_text,
            "answer_text": last_record.answer_text,
            "created_at": last_record.created_at
        }
    else:
        last_record = {}

    # get questions json data from a third-party API
    try:
        new_questions = get_questions(req_question.questions_num)
    except ResponseError as error:
        return {"error": str(error)}

    for raw in new_questions:
        db_question = {
            "question_id": raw["id"],
            "question_text": raw["question"],
            "answer_text": raw["answer"],
            "created_at": raw["created_at"]
        }

        # checking DB for duplicate
        result = insert_question(db_question, session)

        # while question is already existed, get new question
        while result.rowcount == 0:
            try:
                raw = get_questions(1)[0]
            except ResponseError as error:
                return {"error": str(error)}

            db_question = {
                "question_id": raw["id"],
                "question_text": raw["question"],
                "answer_text": raw["answer"],
                "created_at": raw["created_at"]
            }
            result = insert_question(db_question, session)

        session.commit()

    session.close()

    # return last record data if it's existed
    # if not existed return empty dict
    return last_record


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
