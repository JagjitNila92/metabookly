from dataclasses import dataclass


@dataclass
class CurrentUser:
    sub: str           # Cognito user sub — stable unique identifier
    email: str
    groups: list[str]  # Cognito groups: ['retailers', 'admins']

    @property
    def is_admin(self) -> bool:
        return "admins" in self.groups
