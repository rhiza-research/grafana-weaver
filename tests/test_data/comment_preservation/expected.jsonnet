local test_comments_1_rawSql_sql = importstr './assets/test-comments-1-rawSql.sql';

{
  "uid": "test-comments",
  "title": "Comment Preservation Test",
  "panels": [
    {
      "id": 1,
      "type": "graph",
      "targets": [
        {
          "rawSql": test_comments_1_rawSql_sql
        }
      ]
    }
  ]
}
