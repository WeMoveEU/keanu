from sqlalchemy import text, bindparam
# Support functions for CiviCRM tables

# This is not a loader
IGNORE = True


def group_history_max_id(_, conn, group_id):
    sql = """
    SELECT
      max(id)
    FROM {subscription_history}
          WHERE group_id IN :gid
                AND status IN ('Added', 'Removed')
    """.format(
        subscription_history=_.source.table('civicrm_subscription_history')
    )

    return conn.execute(text(sql).bindparams(bindparam('gid', expanding=True)),
                        gid=isinstance(group_id, int) and [group_id] or list(map(str, group_id))
                        )


def group_history(_, conn, group_id, contact_range=None, contact_select=None):
    """Selects subscription history from CiviCRM, for contact_range or contact_select and for
group_id or a list of group ids, if group_id is list.
    """

    if contact_range:
        contact_sql = text("""
                contact_id >= :contact_min AND contact_id < :contact_max
        """).bindparams(contact_min=contact_range[0], contact_max=contact_range[1])
    else:
        contact_sql = """
        contact_id IN ({contact_select})
        """.format(
            contact_select=contact_select
        )

        contact_sql = text(contact_sql).bindparams(*contact_select.get_children())

    sql = """
    SELECT
      group_id,
      contact_id,
      date,
      CASE WHEN status = 'Added' THEN true
                                 ELSE false
      END as is_join
    FROM {subscription_history}
          WHERE group_id IN :gid
                AND status IN ('Added', 'Removed')
                AND {contact_sql}
    ORDER by group_id, contact_id, date
    """.format(
        subscription_history=_.source.table('civicrm_subscription_history'),
        contact_sql=contact_sql
    )

    sql = text(sql).bindparams(*contact_sql.get_children())
    sql = sql.bindparams(bindparam('gid', expanding=True))

    return conn.execute(sql,
                        gid=isinstance(group_id, int) and [group_id] or list(map(str, group_id)))


def sql_for_contacts_who_changed(_, group_id, since_id):
    sql = """
    SELECT
    distinct(contact_id)
    FROM {subscription_history}
    WHERE group_id IN :gid
    AND id > :since_id
    AND status IN ('Added', 'Removed')
    """.format(
        subscription_history=_.source.table('civicrm_subscription_history')
        )

    group_id=isinstance(group_id, int) and [group_id] or list(map(str, group_id))
    sql = text(sql).bindparams(gid=group_id, since_id=since_id)
    return sql

