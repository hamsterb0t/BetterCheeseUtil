import json
import os
import time

from app.constants import USERPATH

class PredictionTemplateService:
    def __init__(self):
        # self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'data')
        self.data_dir = os.path.join(USERPATH, "BCU")
        self.data_file = os.path.join(self.data_dir, 'prediction_templates.json')
        self._ensure_data_dir()
        self._load_data()

    def _ensure_data_dir(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        if not os.path.exists(self.data_file):
            self._save_data({"templates": [], "history": []})

    def _load_data(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except Exception as e:
            print(f"Error loading templates: {e}")
            self.data = {"templates": [], "history": []}

    def _save_data(self, data=None):
        if data:
            self.data = data
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving templates: {e}")

    def get_all(self):
        self._load_data()
        return self.data

    def add_template(self, template):
        self._load_data()
        # Create a simple ID if not present
        if 'id' not in template:
            template['id'] = str(int(time.time() * 1000))
        
        self.data['templates'].append(template)
        self._save_data()
        return self.data

    def delete_template(self, template_id):
        self._load_data()
        self.data['templates'] = [t for t in self.data['templates'] if t.get('id') != template_id]
        self._save_data()
        return self.data

    def update_all_templates(self, templates):
        """Replace the entire templates list (for reordering)"""
        self._load_data()
        self.data['templates'] = templates
        self._save_data()
        return self.data

prediction_template_service = PredictionTemplateService()
