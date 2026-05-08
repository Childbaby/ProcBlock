import traceback
from django.db import connection


def main() -> None:
    try:
        with connection.cursor() as c:
            # Try updating the canonical site id=1 first
            c.execute(
                "UPDATE django_site SET name=%s, domain=%s WHERE id=1",
                ("ProcBase", "localhost:8000"),
            )
            if c.rowcount == 0:
                # Fallback: update any row that looks like the old brand
                c.execute(
                    "UPDATE django_site SET name=%s, domain=%s WHERE name ILIKE %s",
                    ("ProcBase", "localhost:8000", "%ProcBase%"),
                )
        print("SITE_UPDATED")
    except Exception as e:
        traceback.print_exc()
        print("SITE_UPDATE_FAILED", e)


if __name__ == "__main__":
    main()
