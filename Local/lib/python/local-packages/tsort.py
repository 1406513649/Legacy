def tsort(graph, full=True):
    """Create a topologically sorted list

    Parameters
    ----------
    graph : list
        The unsorted graph

    Returns
    -------
    _sorted : list
        The sorted graph

    Notes
    -----
    Repeatedly go through all of the nodes in the graph, moving each of the
    nodes that has all its edges resolved, onto a sequence that forms our
    sorted graph. A node has all of its edges resolved and can be moved once
    all the nodes its edges point to, have been moved from the unsorted graph
    onto the sorted one.

    Examples
    --------
         1
         |
         2
        / \
       6   5
          / \
         3   4

    >>> graph = ((1,2), (2,6,5), (5,3,4), (6,), (3,), (4,))
    >>> tsort(graph)
    [3, 4, 5, 6, 2, 1]

    """
    # Convert the unsorted graph to a hash table.
    graph = dict([(g[0], g[1:]) for g in graph])
    _sorted = []

    # Run until the unsorted graph is empty.
    while graph:
        acyclic = False
        for (node, edges) in graph.items():
            for edge in edges:
                if edge in graph:
                    break
            else:
                acyclic = True
                del graph[node]
                _sorted.append((node, edges))

        if not acyclic:
            # unable to resolve unsorted nodes which means there
            # are nodes with cyclic edges that will never be resolved,
            raise Exception("cyclic dependency encountered")

    if full:
        return _sorted
    return [x[0] for x in _sorted]


if __name__ == "__main__":
    a = tsort(((1,2), (2,6,5), (5,3,4), (6,), (3,), (4,)), full=False)
    print a
