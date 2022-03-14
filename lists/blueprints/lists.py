from flask import Blueprint as BP, render_template, request
from sqlalchemy import select, func

from lists.db import ingredients, ingredients_recipes, engine, recipes


blueprint = BP('lists', __name__, url_prefix='/lists',
               template_folder='/app/lists/templates/lists')


@blueprint.route('/')
def show_recipes():
    with engine.connect() as conn:
        rows = conn.execute(select(recipes.c.name)).fetchall()
        return render_template('choose_for_list.html',
                               recipes=[row[0] for row in rows])


@blueprint.route('/', methods=['GET', 'POST'])
def build_shopping_list():

    """Build the shopping list from a database query
    https://www.db-fiddle.com/f/8bnFVauYvfwbJY6Bwg4D2V/0

    Schema:
    create table ingredients (
    name text primary key,
        aisle text
    );

    create table recipes (
        name text primary key
    );

    create table ingredients_recipes (
        recipe text references recipes,
        ingredient text references ingredients,
        amount integer
    );

    insert into ingredients (name, aisle) values
        ('zuccini', 'produce'),
        ('apple', 'produce'),
        ('sugar', 'middle');

    insert into recipes (name) values ('test');

    insert into recipes (name) values ('test two');

    insert into ingredients_recipes (recipe, ingredient, amount) values
        ('test', 'zuccini', 1),
        ('test', 'apple', 5),
        ('test two', 'sugar', 5),
        ('test two', 'apple', 2);

    Query example:
    select ing.aisle, ing.name, sum(ir.amount)
    from ingredients ing
    left join ingredients_recipes as ir on ir.ingredient = ing.name
    where ir.recipe in ('test', 'test two')
    group by ing.name, ing.aisle
    order by ing.aisle desc
    """
    with engine.connect() as conn:
        sel = select(ingredients.c.aisle, ingredients.c.name,
                     func.sum(ingredients_recipes.c.amount))
        sel = sel.select_from(ingredients
                              .join(ingredients_recipes,
                                    ingredients_recipes.c.ingredient == ingredients.c.id)
                              .join(recipes,
                                    recipes.c.id == ingredients_recipes.c.recipe))
        sel = sel.where(recipes.c.name.in_(request.form.getlist('recipes_for_list')))
        sel = sel.where(~ingredients.c.stocked)
        sel = sel.group_by(ingredients.c.name, ingredients.c.aisle)
        sel = sel.order_by(ingredients.c.aisle.asc())
        rows = conn.execute(sel)

        # Preprocess into aisle -> {'thing': amount} mappings
        aisles = {}
        for result in rows.fetchall():
            if result[0] not in aisles:
                aisles[result[0]] = []
            aisles[result[0]].append({result[1]: result[2]})
        return render_template('shopping_list.html',
                               aisles=aisles)
