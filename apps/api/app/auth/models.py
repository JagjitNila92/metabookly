from dataclasses import dataclass

# Plan tier order — used for >= comparisons in require_plan
PLAN_ORDER = {"free": 0, "starter_api": 1, "intelligence": 2, "enterprise": 3}


@dataclass
class CurrentUser:
    sub: str           # Cognito user sub — stable unique identifier
    email: str
    groups: list[str]  # Cognito groups: ['retailers', 'publishers', 'distributors', 'admins']

    @property
    def is_admin(self) -> bool:
        return "admins" in self.groups

    @property
    def is_publisher(self) -> bool:
        return "publishers" in self.groups or self.is_admin

    @property
    def is_retailer(self) -> bool:
        return "retailers" in self.groups or self.is_admin

    @property
    def is_distributor(self) -> bool:
        return "distributors" in self.groups or self.is_admin
