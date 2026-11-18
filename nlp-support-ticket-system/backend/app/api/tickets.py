from fastapi import APIRouter, Depends, HTTPException, Response

from backend.app.api.dependencies import repository
from backend.app.schemas import Ticket, TicketCreate, TicketUpdate

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.post("", response_model=Ticket, status_code=201)
def create_ticket(body: TicketCreate, repo=Depends(repository)):
    return repo.create_ticket(body.text, body.actual_category)


@router.get("", response_model=list[Ticket])
def list_tickets(repo=Depends(repository)):
    return repo.tickets()


@router.get("/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: int, repo=Depends(repository)):
    ticket = repo.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket not found.")
    return ticket


@router.patch("/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: int, body: TicketUpdate, repo=Depends(repository)):
    get_ticket(ticket_id, repo)
    return repo.update_ticket(ticket_id, body.model_dump(exclude_unset=True))


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: int, repo=Depends(repository)):
    if not repo.delete_ticket(ticket_id):
        raise HTTPException(404, "Ticket not found.")
    return Response(status_code=204)
