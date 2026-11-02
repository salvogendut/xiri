/* Regression for the null-child traversal observed in FAM's polling set. */
#include <cassert>
#include <cstddef>
#include "BTree.h"

int main()
{
    BTree<int, bool> tree;
    assert(tree.first() == 0 && tree.next(10) == 0);
    for (int i=128; i>0; --i) assert(tree.insert(i, true));
    int expected=1;
    for (int key=tree.first(); key; key=tree.next(key)) assert(key==expected++);
    assert(expected==129 && tree.next(128)==0);
    // Scanning an interest can remove it; next(pred) must find its successor.
    expected=1;
    for (int key=tree.first(); key; key=tree.next(key)) {
        assert(key==expected++);
        assert(tree.remove(key));
    }
    assert(expected==129 && tree.size()==0 && tree.first()==0);
    return 0;
}
