# Visit Registration App (visit_regn)

This app handles Visitor Registration and Token Management for the Village Office system.

## Setup

1.  Add `'visit_regn'` to `INSTALLED_APPS` in `settings.py`.
2.  Run migrations:
    ```bash
    python manage.py makemigrations visit_regn
    python manage.py migrate
    ```
3.  Load demo data (optional):
    ```bash
    python manage.py loaddata visit_regn/fixtures/demo_office.json
    ```

## Features

-   **Kiosk Interface**: Visitor registration via Manual, QR (Simulated), or Quick methods.
-   **Token Management**: Daily unique tokens per office (e.g., `050317-20251210-001`).
-   **Staff Queue**: View running tokens, attend, transfer, and complete visits.
-   **Logging**: Full audit trail (VisitLog) for every action.

## Dependencies

-   `accounts` app (for User, Office, Desk models).
-   `routing` module (Optional). If present, `visit_regn` tries to call `routing.services.route_visit(visit)`.

## Testing

Run tests with:
```bash
python manage.py test visit_regn
```

## Shell Example

Create a visit manually in shell:
```python
from visit_regn.models import Visit, Purpose
from accounts.models import Office, User

office = Office.objects.first()
user = User.objects.get(username='VISITOR')
purpose = Purpose.objects.first()

visit = Visit.create_from_kiosk(
    {'name': 'Test User', 'mobile': '1234567890', 'purpose': purpose},
    office=office,
    user=user
)
print(visit.token)
```
