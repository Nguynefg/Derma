-- Run in BenhLy. Adds an index only if no usable unfiltered index leads with name.
IF OBJECT_ID(N'dbo.tbldiseases', N'U') IS NULL
    THROW 50001, 'dbo.tbldiseases was not found in the selected database.', 1;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes AS i
    JOIN sys.index_columns AS ic
      ON ic.object_id = i.object_id AND ic.index_id = i.index_id
    JOIN sys.columns AS c
      ON c.object_id = ic.object_id AND c.column_id = ic.column_id
    WHERE i.object_id = OBJECT_ID(N'dbo.tbldiseases')
      AND i.type IN (1, 2)
      AND i.is_disabled = 0
      AND i.is_hypothetical = 0
      AND i.has_filter = 0
      AND ic.key_ordinal = 1
      AND c.name = N'name'
)
BEGIN
    CREATE NONCLUSTERED INDEX ix_tbldiseases_name
        ON dbo.tbldiseases (name);
    PRINT 'Created ix_tbldiseases_name';
END
ELSE
    PRINT 'A usable index beginning with name already exists.';
