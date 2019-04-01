function usdFormatter(v, axis) {
    return "$" + v.toFixed(0);
}

var data = [
  {color: "#6CB885", data: trade_data['core']['bids']['prices'], label: "Core Bids", lines: {show: false}, points: {show: true, symbol: partial(point, 'core', 'bids', 0.7)}},
  {color: "blue", data: trade_data['core']['asks']['prices'], label: "Core Asks", lines: {show: false}, points: {show: true, symbol: partial(point, 'core', 'asks', 0.7)}},
  {color: "black", data: fundamental_values_data, label: "fundamental values", hoverable: false},
];
  
draw_main_graph = function() {
  $.plot($("#gryphon-graph"),
    data,
    {
      grid: {
        hoverable: true,
        markings: [],
      },
      series: {
        curvedLines: { active: true },
        lines: {
          show: true,
          lineWidth: 2
        },
        shadowSize: 0
      },
      xaxes: [{
        mode: 'time',
        min: start_timestamp,
        max: end_timestamp,
      }],
      yaxis: {
        labelWidth: 30
      },
      yaxes: [{
        tickFormatter: usdFormatter,
      }],
      legend: { position: 'sw' }
  });

  $("<div id='tooltip'></div>").css({
    position: "absolute",
    display: "none",
    border: "3px solid #dbd5a8",
    padding: "2px 10px",
    "background-color": "#F3ECBC",
    opacity: 0.80
  }).appendTo("body");

  $("#gryphon-graph").bind("plothover", function (event, pos, item) {
      if(item) {
        // item.datapoint only has the graphable data (timestamp and price)
        // but it gives us access to the full series data
        var full_datapoint = item.series.data[item.dataIndex];
        var exchange_name = full_datapoint[2];
        var volume = full_datapoint[3];
        var price = full_datapoint[4];
        var fee = full_datapoint[5];
        var order_id = full_datapoint[6];
        var content =
          "<p>" +
            exchange_name + "</br>" +
            volume + " @ " + price + "</br>" +
            "Fee: " + fee + "</br>" +
            "Order ID: " + order_id + "</br>" +
          "</p>"
        $("#tooltip").html(content)
          .css({top: item.pageY+20, left: item.pageX+20})
          .fadeIn(200);
      } else {
        $("#tooltip").hide();
      }
  });
}

draw_revenue_position_graph = function() {
  $.plot($("#revenue-graph"),
    [{
        color: "green", 
        data: revenue_series,
        label: "Revenue",
        lines: {
          lineWidth: 5,
        },
      },
      {
        color: '#ED9121',
        data: position_series, 
        label: "Position", 
        yaxis: 2,
        lines: {
          show: true,
          steps: true,
        }
      },
    ],
    {
      series: {
        curvedLines: { active: true },
        lines: {
          show: true,
        }
      },
      xaxes: [{ 
        mode: 'time',
        min: start_timestamp,
        max: end_timestamp,
      }],
      yaxes: [{
        tickFormatter: usdFormatter
      },
      {
        alignTicksWithAxis: 1,
        position: "right",
        min: position_graph_min,
        max: position_graph_max,
        labelWidth: 30
      },
      ],
      legend: { position: 'sw' }
  });
}

$(document).ready(function() {
  function usdFormatter(v, axis) {
      return "$" + v.toFixed(0);
  }

  draw_main_graph();
  draw_revenue_position_graph();
});
