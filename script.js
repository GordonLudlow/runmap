$(function(){ 
    $("#myTable")
      .sortable({ items: "tr.sortable" })
      .dragtable({dragHandle: ".dragHandle"})
      .tablesorter();
  })