"""Stable Vietnamese alphabetical ordering, applied before pagination."""
from sqlalchemy import case, func

LETTERS = list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ')

def alphabetical(db, title):
    dialect = db.get_bind().dialect.name
    trimmed = func.ltrim(title)
    first = func.substring(trimmed, 1, 1) if dialect == 'mssql' else func.substr(trimmed, 1, 1)
    name = trimmed.collate('Vietnamese_100_CI_AS') if dialect == 'mssql' else func.lower(trimmed)
    return [case((first.in_(LETTERS), 0), else_=1), name]
