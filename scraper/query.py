import os

def join_with_or(path):
    final_query = ""
    with open(path, 'r') as f:
        for line in f:
            term = line.rstrip()
            query = '({})'.format(term)
            final_query += query
            final_query += ' OR '
    # Get rid of final OR.
    final_query = final_query[:len(final_query) - 4]
    final_query ='({})'.format(final_query)
    return final_query 

def craft_query(query_dir):
    or_path = os.path.join(query_dir, 'OR.txt')    
    not_path = os.path.join(query_dir, 'NOT.txt')
    ors = join_with_or(or_path)
    nots = join_with_or(not_path)
    final_query = '{} NOT {}'.format(ors, nots)
    return final_query
