local script_js = importstr './input_assets/panel-script.js';
local query_sql = importstr './input_assets/query.sql';

{
  "uid": "test-build",
  "title": "Build Test Dashboard",
  "panels": [
    {
      "id": 1,
      "type": "custom",
      "options": {
        "script": script_js
      }
    },
    {
      "id": 2,
      "type": "graph",
      "targets": [
        {
          "rawSql": query_sql
        }
      ]
    }
  ]
}
