from dataclasses import dataclass


@dataclass
class CurrentUser:
    sub: str           # Cognito user sub — stable unique identifier
    email: str
    groups: list[str]  # Cognito groups: ['retailers', 'admins']

    @property
    def is_admin(self) -> bool:
        return "admins" in self.groups

    @property
    def is_publisher(self) -> bool:
        return "publishers" in self.groups or self.is_admin

    @property
    def is_retailer(self) -> bool:
        return "retailers" in self.groups or self.is_admin
