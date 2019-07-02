function usdFormatter(v, axis) {
    padding = 4 - v.toString().length;
    console.log(padding);

    if (padding > 0) {
      return "$" + v.toFixed(6);
    } else {
      return "$" + v.toFixed(6);
    }
}

var data = [
  {color: "#6CB885", data: trade_data['core']['bids']['prices'], label: "Bids", lines: {show: false}, points: {show: true, symbol: partial(point, 'core', 'bids', 0.7)}},
  {color: "blue", data: trade_data['core']['asks']['prices'], label: "Asks", lines: {show: false}, points: {show: true, symbol: partial(point, 'core', 'asks', 0.7)}},
];
  
draw_main_graph = function() {
  $.plot($("#gryphon-graph"),
    data,
    {
      grid: {
        labelMargin: 20,
        hoverable: true,
        markings: [],
        margin: {right: 55,},
        /*backgroundColor: '#EDEFF2',*/
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
        showTickLabels: false,
        font: {
          'family': 'Roboto Mono',
        },
      }],
      yaxes: [{
        tickFormatter: usdFormatter,
        ticks: 4,
       /* tickSize: 15,*/
        font: {
          'family': 'Roboto Mono',
        },
      }],
      legend: {
        position: 'se',
        noColumns: 2,
      },
      watermark: {
        opacity: 0.1,
        mode: 'text',
        position: 'sw',
        text: 'BTC-USD TRADES',
        font: '60px Arial',
        margin: [50, 0],
      },
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
      grid: {
        labelMargin: 20,
        /*backgroundColor: '#EDEFF2',*/
        margin: {},
      },
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
        font: {
          'family': 'Roboto Mono',
        },
      }],
      yaxes: [{
        tickFormatter: usdFormatter,
        /*ticks: [-1000, 1000, 3000, 5000, 7000, 9000],*/
        tickSize: 1500,
        /*ticks: 4,*/
        font: {
          'family': 'Roboto Mono',
        },
      },
      {
        /*alignTicksWithAxis: 1,*/
        position: "right",
        min: position_graph_min,
        max: position_graph_max,
        show: true,
        labelWidth: 30,
        font: {
          'family': 'Roboto Mono',
        },
      },
      ],
      legend: {
        position: 'se',
        noColumns: 2,
      },
      watermark: {
        opacity: 0.1,
        mode: 'text',
        position: 'sw',
        text: 'POSITION/P&L',
        font: '60px Arial',
        margin: [50, 0],
      },
  });
}

$(document).ready(function() {
  draw_main_graph();
  draw_revenue_position_graph();
});
