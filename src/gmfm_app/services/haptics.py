"""
Haptic Feedback Service - Optimized for Nothing Phone 2a
Uses Flet's haptics API with patterns suited for linear vibration motors.
"""
import flet as ft


class HapticService:
    """
    Haptic feedback patterns optimized for Nothing Phone 2a's linear motor.
    The Nothing Phone 2a has a responsive X-axis linear vibration motor.
    """
    
    @staticmethod
    def tap(page: ft.Page):
        """Light tap - for button presses, selections."""
        try:
            page.haptic_feedback(ft.HapticFeedbackType.LIGHT_IMPACT)
        except:
            pass
    
    @staticmethod
    def select(page: ft.Page):
        """Selection feedback - for scoring items, toggles."""
        try:
            page.haptic_feedback(ft.HapticFeedbackType.SELECTION_CLICK)
        except:
            pass
    
    @staticmethod
    def success(page: ft.Page):
        """Success feedback - for saves, completions."""
        try:
            page.haptic_feedback(ft.HapticFeedbackType.MEDIUM_IMPACT)
        except:
            pass
    
    @staticmethod
    def heavy(page: ft.Page):
        """Heavy feedback - for celebrations, important actions."""
        try:
            page.haptic_feedback(ft.HapticFeedbackType.HEAVY_IMPACT)
        except:
            pass
    
    @staticmethod
    def warning(page: ft.Page):
        """Warning feedback - for destructive actions, errors."""
        try:
            # Double tap pattern for warning
            page.haptic_feedback(ft.HapticFeedbackType.MEDIUM_IMPACT)
        except:
            pass
    
    @staticmethod
    def error(page: ft.Page):
        """Error feedback - for failed actions."""
        try:
            page.haptic_feedback(ft.HapticFeedbackType.HEAVY_IMPACT)
        except:
            pass


# Convenience functions
def tap(page: ft.Page):
    HapticService.tap(page)

def select(page: ft.Page):
    HapticService.select(page)

def success(page: ft.Page):
    HapticService.success(page)

def heavy(page: ft.Page):
    HapticService.heavy(page)

def warning(page: ft.Page):
    HapticService.warning(page)

def error(page: ft.Page):
    HapticService.error(page)
