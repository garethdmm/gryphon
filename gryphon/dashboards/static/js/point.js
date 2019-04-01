/*
This applies some number of arguments to a function and gives you back
a new function which can take the rest of the arguments
we are using it here for calling point() with some of our arguments (tag, side, alpha)
and letting flot pass in its arguments (ctx, etc)
http://stackoverflow.com/questions/321113/how-can-i-pre-set-arguments-in-javascript-function-call-partial-function-appli
*/
function partial(func /*, 0..n args */) {
  var args = Array.prototype.slice.call(arguments, 1);
  return function() {
    var allArguments = args.concat(Array.prototype.slice.call(arguments));
    return func.apply(this, allArguments);
  };
}

function point(tag, side, alpha, ctx, x, y, radius, shadow) {
  data = trade_data[tag][side]

  if (data.count == undefined) {
    data.count = 0;
    // max hacks yo. The only persistent reference we have to a point is it's xy coords
    // so we use that to store its volume-based radius
    // then when flot redraws the point (for the hover effect) we can look it up
    data.x_y_radius_map = {}
  }

  x_y_key = x + "," + y

  if(data.count < data['volumes'].length) {
    // first pass through the data (the main graph draw)
    radius = BASE_POINT_RADIUS * Math.sqrt(data['volumes'][data.count]);
    data.x_y_radius_map[x_y_key] = radius;
  } else if (x_y_key in data.x_y_radius_map) {
    // if we are redrawing a point on the same coordinates
    // it is because flot wants to draw a hover highlight
    // we look up the correct radius for that point
    // so that the hover blur fits the radius of the point
    radius = data.x_y_radius_map[x_y_key];
  } else {
    // if we are redrawing a point on different coordinates
    // it is because the window (and graph) have been resized
    // we want to reset everything, because the old xy coords are invalid
    // after this reset, flot will redraw all the points on new coords
    // which will hit the "first pass" case above since we have reset the count
    data.count = 0;
    data.x_y_radius_map = {};
    // but we still need to handle this one initial point
    radius = BASE_POINT_RADIUS * Math.sqrt(data['volumes'][data.count]);
    data.x_y_radius_map[x_y_key] = radius;
  }

  data.count++;
  ctx.globalAlpha=alpha;

  ctx.arc(x, y, radius, 0, shadow ? Math.PI : Math.PI * 1.0, side == "asks");
}
