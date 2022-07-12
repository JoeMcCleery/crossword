import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        # Loop all domains
        for var in self.domains:
            # Filter list of words in domain to those that contain correct number of letters
            self.domains[var] = list(filter(lambda word: len(word) == var.length, self.domains[var]))

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        # Get intersection
        intersection = self.crossword.overlaps[x, y]
        # If there is an intersection
        if intersection is not None:
            # Get number of words in domain
            num = len(self.domains[x])
            # Init list of words to keep
            keep = []
            # Loop words in domain of x
            for x_word in self.domains[x]:
                # Loop words in domain of y
                for y_word in self.domains[y]:
                    # If intersection does have same letter
                    if x_word[intersection[0]] == y_word[intersection[1]]:
                        # Keep this word in the domain
                        keep.append(x_word)
                        # Don't bother checking other y_words for this x_word
                        break
            # Set new values for domain of x
            self.domains[x] = keep
            # Return true if changed number of words, otherwise false
            return len(keep) != num
        # No intersection
        return False

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        # Initialise arcs
        if arcs is None:
            arcs = []
            # Loop all vars
            for v1 in self.domains:
                # Loop neighbors of v1
                for v2 in self.crossword.neighbors(v1):
                    # Add arc
                    arcs.append((v1, v2))
        # Keep looping until no arcs left
        while len(arcs) > 0:
            (x, y) = arcs.pop()
            # If change was made to domains
            if self.revise(x, y):
                # If no solutions for var x, then no possible solution exists
                if len(self.domains[x]) == 0:
                    return False
                # Loop all neighbors of var x excluding var y
                for z in self.crossword.neighbors(x) - {y}:
                    # Add new_arc to list
                    arcs.append((z, x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        # Loop all vars
        for var in self.domains:
            # If var not in assignment
            if var not in assignment:
                return False
        # All vars are in assignment
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Loop all vars
        for v1 in assignment:
            # If word has incorrect number of letters
            if len(assignment[v1]) != v1.length:
                return False
            for v2 in assignment:
                # Ignore self
                if v1 == v2:
                    continue
                # If word is the same
                if assignment[v1] == assignment[v2]:
                    return False
                # If there is an intersection
                intersection = self.crossword.overlaps[v1, v2]
                if intersection is not None:
                    # If letter is not the same
                    if assignment[v1][intersection[0]] != assignment[v2][intersection[1]]:
                        return False
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        neighbors = self.crossword.neighbors(var) - {*assignment}
        return sorted(self.domains[var], key=lambda word: self.count_removed_in_neighbors(var, word, neighbors))

    def count_removed_in_neighbors(self, var, word, neighbors):
        count = 0
        # Loop neighbors of var
        for neighbor in neighbors:
            intersection = self.crossword.overlaps[var, neighbor]
            # Loop words in neighbor
            for w in self.domains[neighbor]:
                # If words match or intersections don't match
                if word == w or word[intersection[0]] != w[intersection[1]]:
                    count += 1
        return count

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        # Get list of unassigned vars
        unassigned = list({*self.domains} - {*assignment})
        # Sort unassigned
        unassigned.sort(key=lambda v: len(self.domains[v]) - len(self.crossword.neighbors(v)) * 0.001)
        return unassigned[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        # Return assignment if complete
        if self.assignment_complete(assignment):
            return assignment
        # Get unassigned var
        var = self.select_unassigned_variable(assignment)
        # Loop order domain values
        for value in self.order_domain_values(var, assignment):
            # Add value to assignment
            assignment[var] = value
            # If value is consistent with assignment
            if self.consistent(assignment):
                # Find result
                result = self.backtrack(assignment)
                # If no result found
                if result is None:
                    # Remove value from assignment
                    del assignment[var]
                else:
                    return result
            else:
                # Remove value from assignment
                del assignment[var]
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
