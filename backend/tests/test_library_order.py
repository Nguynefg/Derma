from sqlalchemy import create_engine, select, literal, union_all
from sqlalchemy.orm import Session
from sqlalchemy.dialects import mssql
from types import SimpleNamespace
from app.modules.library.library_order import alphabetical

def test_letters_first_numbers_last_and_pagination_stable():
    engine=create_engine('sqlite://')
    values=union_all(*[select(literal(name).label('name'),literal(i).label('id')) for i,name in enumerate(['2 ethanol','Ban','Acne','(chemical)','Acne','Đau'])]).subquery()
    with Session(engine) as db:
        ordered=select(values).order_by(*alphabetical(db,values.c.name),values.c.id)
        rows=db.execute(ordered).all()
        assert [r.name for r in rows[:3]]==['Acne','Acne','Ban']
        assert [r.name for r in rows[-2:]]==['(chemical)','2 ethanol']
        assert db.execute(ordered.offset(2).limit(2)).all()==rows[2:4]

def test_sql_server_uses_vietnamese_collation_before_pagination():
    db=SimpleNamespace(get_bind=lambda:SimpleNamespace(dialect=mssql.dialect()))
    query=select(literal('Đau').label('name')).order_by(*alphabetical(db,literal('Đau'))).offset(12).limit(12)
    sql=str(query.compile(dialect=mssql.dialect()))
    assert 'Vietnamese_100_CI_AS' in sql and 'substring' in sql
