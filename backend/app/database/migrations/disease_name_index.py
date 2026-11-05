"""Add a name-leading index to existing databases as well as fresh installs."""
from sqlalchemy import inspect, text
from app.database.models import Disease


def ensure_name_index(engine):
    with engine.begin() as connection:
        if connection.dialect.name == 'mssql':
            existing = connection.scalar(text('''
                SELECT TOP (1) i.name
                FROM sys.indexes i
                JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
                JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
                WHERE i.object_id=OBJECT_ID(N'dbo.tbldiseases')
                  AND i.type IN (1,2) AND i.is_disabled=0
                  AND i.is_hypothetical=0 AND i.has_filter=0
                  AND ic.key_ordinal=1 AND c.name=N'name'
            '''))
        else:
            existing = next((i['name'] for i in inspect(connection).get_indexes('tbldiseases')
                             if i['column_names'] and i['column_names'][0]=='name'
                             and not any(k.endswith('_where') and v is not None
                                         for k,v in i.get('dialect_options',{}).items())), None)
        if existing:
            return {'status':'already_exists','index':existing}
        index = next(i for i in Disease.__table__.indexes if i.name=='ix_tbldiseases_name')
        index.create(connection)
    return {'status':'created','index':index.name}
