from collections import deque
from heapq import heappop, heappush


class WaitingVisitorQueue:
    def __init__(self, visitors=None):
        self.items = deque(visitors or [])

    def enqueue(self, visitor):
        self.items.append(visitor)

    def dequeue(self):
        return self.items.popleft() if self.items else None

    def as_list(self):
        return list(self.items)


class VIPPriorityQueue:
    def __init__(self):
        self.heap = []

    def push(self, priority, visitor):
        heappush(self.heap, (priority, visitor.created_at, visitor))

    def pop(self):
        return heappop(self.heap)[2] if self.heap else None


def college_id_hash(records):
    return {record.college_id.lower(): record for record in records if record.college_id}


def binary_search_visitors(sorted_visitors, visitor_id):
    low, high = 0, len(sorted_visitors) - 1
    while low <= high:
        mid = (low + high) // 2
        current_id = sorted_visitors[mid].id
        if current_id == visitor_id:
            return sorted_visitors[mid]
        if current_id < visitor_id:
            low = mid + 1
        else:
            high = mid - 1
    return None


def approval_path(start_role, target_role):
    graph = {
        "public": ["security"],
        "security": ["staff", "principal", "management"],
        "staff": ["security"],
        "principal": ["security"],
        "management": ["security"],
    }
    queue = deque([(start_role, [start_role])])
    visited = {start_role}
    while queue:
        role, path = queue.popleft()
        if role == target_role:
            return path
        for nxt in graph.get(role, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path + [nxt]))
    return []
