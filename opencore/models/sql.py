view_count = """
select count(*)
from  requests 
where path = :path
and query_string = ''
""" 