local test_params_custom_config_js = importstr './assets/test-params-custom-config.js';

{
  "uid": "test-params",
  "title": "Parameterized Filename Test",
  "panels": [
    {
      "id": 10,
      "type": "custom",
      "options": {
        "script": test_params_custom_config_js
      }
    }
  ]
}
