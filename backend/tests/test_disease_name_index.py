from sqlalchemy import create_engine, inspect, Index
from app.database.models import Disease
from app.database.migrations.disease_name_index import ensure_name_index


def test_add_index_to_existing_table_and_repeat_safely():
    engine=create_engine('sqlite://')
    Disease.__table__.create(engine)
    index=next(i for i in Disease.__table__.indexes if i.name=='ix_tbldiseases_name')
    index.drop(engine)
    assert ensure_name_index(engine)['status']=='created'
    assert ensure_name_index(engine)['status']=='already_exists'
    assert [i['name'] for i in inspect(engine).get_indexes('tbldiseases')].count(index.name)==1


def test_existing_equivalent_index_is_reused():
    engine=create_engine('sqlite://')
    Disease.__table__.create(engine)
    expected=next(i for i in Disease.__table__.indexes if i.name=='ix_tbldiseases_name')
    expected.drop(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql('CREATE INDEX custom_name_lookup ON tbldiseases(name, disease_id)')
    assert ensure_name_index(engine)=={'status':'already_exists','index':'custom_name_lookup'}
    assert not any(i['name']==expected.name for i in inspect(engine).get_indexes('tbldiseases'))
