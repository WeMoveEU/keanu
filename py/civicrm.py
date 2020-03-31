from sqlalchemy import text, bindparam
from util import nest_sql
# Support functions for CiviCRM tables

# This is not a loader
IGNORE = True


def group_history_max_id(_, group_id):
    gid=isinstance(group_id, int) and [group_id] or list(group_id)

    sql = text("""
    SELECT
      max(id)
    FROM {subscription_history}
          WHERE group_id IN :gid
                AND status IN ('Added', 'Removed')
    """.format(
        subscription_history=_.source.table('civicrm_subscription_history')
    )).bindparams(gid=gid)


    return _.source.connection().execute(sql).fetchone()[0]


def group_history(_, group_id, hist_max_id, contact_range=None, contact_select=None):
    """Selects subscription history from CiviCRM, for contact_range or contact_select and for
group_id or a list of group ids, if group_id is list.
    """

    sql = """
    SELECT
      sh.group_id,
      sh.contact_id,
      sh.date,
      CASE WHEN sh.status = 'Added' THEN true
                                 ELSE false
      END as is_join
    FROM {subscription_history} sh
    JOIN contact c ON sh.contact_id = c.id
          WHERE group_id IN :gid
                AND sh.id <= :hist_max_id
                AND sh.status IN ('Added', 'Removed')
                AND {contact_criteria}

    ORDER by group_id, contact_id, date
    """

    if contact_range:
        sql = text(sql.format(
            subscription_history=_.source.table('civicrm_subscription_history'),
            contact_criteria="""
                sh.contact_id >= :contact_min AND sh.contact_id < :contact_max
        """
        )).bindparams(contact_min=contact_range[0],
                      contact_max=contact_range[1])

    else:
        sql = sql.format(
            subscription_history=_.source.table('civicrm_subscription_history'),
            contact_criteria="""
            sh.contact_id IN ({contact_select})
            """
        )

        sql = nest_sql(sql,  contact_select=contact_select)

    group_id=isinstance(group_id, int) and [group_id] or list(group_id)
    return _.source.connection().execute(sql, gid=group_id, hist_max_id=hist_max_id)


def sql_for_contacts_who_changed_group(_, group_id, since_id, until_id):
    sql = """
    SELECT
    distinct(contact_id)
    FROM {subscription_history}
    WHERE group_id IN :gid
    AND id >= :since_id AND id <= :until_id
    AND status IN ('Added', 'Removed')
    """.format(
        subscription_history=_.source.table('civicrm_subscription_history')
        )

    group_id=isinstance(group_id, int) and [group_id] or list(group_id)
    sql = text(sql).bindparams(gid=group_id, since_id=since_id, until_id=until_id)
    return sql

