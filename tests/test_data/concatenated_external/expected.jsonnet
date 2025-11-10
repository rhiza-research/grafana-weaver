local colors_js = importstr './assets/colors.js';
local utils_js = importstr './assets/utils.js';

{
  "uid": "test-concat",
  "title": "Concatenated External Test",
  "panels": [
    {
      "id": 1,
      "type": "custom",
      "options": {
        "script": colors_js + utils_js
      }
    }
  ]
}
