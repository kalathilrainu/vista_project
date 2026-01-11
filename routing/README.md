# Routing App

This app handles the flow of visits (tokens) through the Village Office. It manages desk assignments, queues, and status updates.

## Key Components

### Models
- **DeskQueue**: Represents the active assignment of a visit to a [Desk]. Ordered by `assigned_at` to enforce FIFO.
- **RoutingRule**: Maps `(Office, Purpose)` to a default `Desk` for auto-routing.

### Services
- `route_visit(visit)`: Main entry point. Attempts auto-routing based on `RoutingRule`. If no rule fits, sends to VO Queue (fallback).
- `assign_visit_to_desk`: Moves token to a specific desk. Updates `Visit.current_desk` and `DeskQueue`.
- `attend_visit`: Locks token to a user/staff member. Sets status `IN_PROGRESS`.
- `transfer_visit`: Moves token from one desk to another. Logs `TRANSFERRED`.

### Views
- **VisitQueueView**: Office-wide dashboard of all tokens.
- **DeskQueueView**: Personal queue for the logged-in staff's desk.
- **VORoutingView**: Special view for Village Officer to override or route pending tokens.

### Extension Points
- **Files/Tapal**: The `RoutingRule` and `DeskQueue` logic can be extended or replicated for physical files. `RoutingRule` currently links to `Purpose` (from Visit), but could be generic relation or separate `FileRoutingRule`.

## Integration
- **Visit_Regn**: Creates the visit. Calls `route_visit` after creation.
- **Accounts**: Provides `Office`, `Desk`, `User`.

## Testing
Run `python manage.py test routing` to verify logic.
