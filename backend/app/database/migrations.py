import re

from sqlalchemy import inspect
from sqlalchemy import text


_TICKET_NUMBER_PATTERN = re.compile(r"^TKT-(\d+)$")


def ensure_ticket_number_column(engine):
    with engine.begin() as connection:
        columns = {
            column["name"].casefold()
            for column in inspect(connection).get_columns("tickets")
        }
        if "ticketnumber" not in columns:
            connection.exec_driver_sql(
                'ALTER TABLE tickets ADD COLUMN "TicketNumber" VARCHAR'
            )

        tickets = connection.execute(
            text('SELECT id, "TicketNumber" FROM tickets ORDER BY id')
        ).fetchall()
        existing_numbers = {
            ticket_number
            for _, ticket_number in tickets
            if ticket_number is not None
        }
        numeric_suffixes = [
            int(match.group(1))
            for ticket_number in existing_numbers
            if (match := _TICKET_NUMBER_PATTERN.fullmatch(ticket_number))
        ]
        next_number = max(numeric_suffixes, default=0) + 1

        for ticket_id, ticket_number in tickets:
            if ticket_number is not None:
                continue

            generated_number = f"TKT-{ticket_id:03d}"
            if generated_number in existing_numbers:
                while f"TKT-{next_number:03d}" in existing_numbers:
                    next_number += 1
                generated_number = f"TKT-{next_number:03d}"
                next_number += 1

            connection.execute(
                text(
                    'UPDATE tickets SET "TicketNumber" = :ticket_number '
                    "WHERE id = :ticket_id"
                ),
                {"ticket_number": generated_number, "ticket_id": ticket_id},
            )
            existing_numbers.add(generated_number)

        connection.exec_driver_sql(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_tickets_ticket_number '
            'ON tickets ("TicketNumber")'
        )
