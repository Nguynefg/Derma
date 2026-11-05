from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import Session
from app.database.models import Base, Disease
from app.modules.library.library_pagination import article_page

def test_narrow_pagination_preserves_order_and_never_sorts_article_text():
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as db:
        for i,name in enumerate(['Beta','Alpha','Alpha','Zeta']):
            db.add(Disease(slug=str(i),name=name,english_name=name,category='test',summary='s',details='Long text '*500,risk_factors='',prevention='',aliases=[]))
        db.commit()
        statements=[]
        def capture(connection,cursor,statement,*args):statements.append(statement)
        event.listen(engine,'before_cursor_execute',capture)
        query=select(Disease)
        ordering=[Disease.name,Disease.id]
        expected=list(db.scalars(query.order_by(*ordering)))
        statements.clear()
        actual=article_page(db,query,ordering,2,2)
        assert [r.id for r in actual]==[r.id for r in expected[2:4]]
        assert len(statements)==2
        assert 'details' not in statements[0].split('FROM')[0]
        assert 'ORDER BY' not in statements[1]
        assert article_page(db,query,ordering,10,2)==[]
        event.remove(engine,'before_cursor_execute',capture)
