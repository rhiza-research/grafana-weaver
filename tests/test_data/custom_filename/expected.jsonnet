local shared_utils_js = importstr './assets/shared-utils.js';

{
  "uid": "test-custom",
  "title": "Custom Filename Test",
  "panels": [
    {
      "id": 5,
      "type": "custom",
      "options": {
        "script": shared_utils_js
      }
    }
  ]
}
