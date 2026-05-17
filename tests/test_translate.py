import json
import os
import sys
import types
import unittest
from unittest.mock import patch

from scripts import translate


class FakeCompletions:
    last_model = None

    def create(self, **kwargs):
        self.__class__.last_model = kwargs["model"]
        content = {
            "title_zh": "中文标题",
            "summary_en": "English summary",
            "summary_zh": "中文摘要",
        }
        message = types.SimpleNamespace(content=json.dumps(content))
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])


class FakeOpenAIClient:
    last_api_key = None
    last_base_url = None

    def __init__(self, api_key=None, base_url=None):
        self.__class__.last_api_key = api_key
        self.__class__.last_base_url = base_url
        self.chat = types.SimpleNamespace(completions=FakeCompletions())


class TranslateProviderTests(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_patch.start()
        FakeOpenAIClient.last_api_key = None
        FakeOpenAIClient.last_base_url = None
        FakeCompletions.last_model = None

    def tearDown(self):
        self.env_patch.stop()

    def test_deepseek_env_uses_deepseek_base_url_and_model(self):
        fake_openai = types.SimpleNamespace(OpenAI=FakeOpenAIClient)

        with patch.dict(sys.modules, {"openai": fake_openai}):
            os.environ["DEEPSEEK_API_KEY"] = "deepseek-key"
            articles = [
                {
                    "title": "Title",
                    "summary_raw": "Raw summary",
                }
            ]

            translate.translate_and_summarise(articles)

        self.assertEqual(FakeOpenAIClient.last_api_key, "deepseek-key")
        self.assertEqual(FakeOpenAIClient.last_base_url, "https://api.deepseek.com")
        self.assertEqual(FakeCompletions.last_model, "deepseek-v4-flash")

    def test_deepseek_model_can_be_overridden(self):
        fake_openai = types.SimpleNamespace(OpenAI=FakeOpenAIClient)

        with patch.dict(sys.modules, {"openai": fake_openai}):
            os.environ["DEEPSEEK_API_KEY"] = "deepseek-key"
            os.environ["DEEPSEEK_MODEL"] = "deepseek-v4-pro"
            translate.translate_and_summarise([{"title": "Title", "summary_raw": ""}])

        self.assertEqual(FakeCompletions.last_model, "deepseek-v4-pro")


if __name__ == "__main__":
    unittest.main()
