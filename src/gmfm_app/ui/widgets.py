from kivy.metrics import dp
from kivy.properties import NumericProperty, OptionProperty, ObjectProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRectangleFlatButton
from kivy.uix.behaviors import ButtonBehavior

class ScoreButton(MDRectangleFlatButton):
    value = OptionProperty("NT", options=["0", "1", "2", "3", "NT"])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.width = dp(40)
        self.height = dp(36)
        self.font_style = "Caption"
        self.padding = (dp(0), dp(0))

class ScoreSelector(MDBoxLayout):
    score = NumericProperty(None, allownone=True)
    item_number = NumericProperty(0)
    callback = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.spacing = dp(2)
        self.size_hint = (None, None)
        self.height = dp(40)
        self.adaptive_width = True
        
        self._buttons = {}
        for val in ["0", "1", "2", "3", "NT"]:
            btn = ScoreButton(text=val, value=val)
            btn.bind(on_release=lambda x, v=val: self.set_score(v))
            self.add_widget(btn)
            self._buttons[val] = btn
            
    def set_score(self, value):
        if value == "NT":
            self.score = None
        else:
            self.score = int(value)
        
        self._update_buttons(value)
        if self.callback:
            self.callback(self.item_number, self.score)

    def _update_buttons(self, active_value):
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        for val, btn in self._buttons.items():
            if val == active_value:
                btn.md_bg_color = app.theme_cls.primary_color
                btn.text_color = [1, 1, 1, 1]
            else:
                btn.md_bg_color = [0, 0, 0, 0]  # Transparent
                btn.text_color = app.theme_cls.text_color

    def update_state(self, score):
        self.score = score
        val = str(score) if score is not None else "NT"
        self._update_buttons(val)

