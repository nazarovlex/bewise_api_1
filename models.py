from sqlalchemy import Column, Integer, Text, DateTime
from database import Base
from pydantic import BaseModel


# postgres table
class QuestionsTable(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, unique=True)
    question_text = Column(Text)
    answer_text = Column(Text)
    created_at = Column(DateTime)


# requests models
class QuestionRequest(BaseModel):
    questions_num: int
