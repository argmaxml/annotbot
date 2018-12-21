$(function(){
    var textAreas = document.getElementsByTagName('textarea');

    Array.prototype.forEach.call(textAreas, function(elem) {
    elem.placeholder = elem.placeholder.replace(/\\n/g, '\n');
    });

 $('.btn-circle').on('click',function(){
   if (!validate()) {
       return false;
   }
   $('.btn-circle.btn-info').removeClass('btn-info').addClass('btn-default');
   $(this).addClass('btn-info').removeClass('btn-default').blur();
 });

 $('.next-step, .prev-step').on('click', function (e){
   if (!validate()) {
       return false;
   }
   var $activeTab = $('.tab-pane.active');

   $('.btn-circle.btn-info').removeClass('btn-info').addClass('btn-default');

   if ( $(e.target).hasClass('next-step') )
   {
      var nextTab = $activeTab.next('.tab-pane').attr('id');
      $('[href="#'+ nextTab +'"]').addClass('btn-info').removeClass('btn-default');
      $('[href="#'+ nextTab +'"]').tab('show');
   }
   else
   {
      var prevTab = $activeTab.prev('.tab-pane').attr('id');
      $('[href="#'+ prevTab +'"]').addClass('btn-info').removeClass('btn-default');
      $('[href="#'+ prevTab +'"]').tab('show');
   }
 });
});

$("#txt_botname").on("input", function () {document.getElementById("spn_botname").textContent=document.getElementById("txt_botname").value;})

function validate() {
    var valid = true;
    var bot_name     = "" + document.getElementById("txt_botname").value;
    var bot_desc     = "" + document.getElementById("txt_desc").value;
    var example_data = "" + document.getElementById("txt_data").value;
    var classes      = "" + document.getElementById("txt_classes").value;
    valid = classes.split('\n').map(function (x) {return ((x.length>0) && (x[0]=='/'))||(x.length<10);}).reduce(function (x,y) {return x && y;},true);
    if (!valid) {
        alert("Class name cannot be longer than 10 characters");
        return false;
    }
    valid = example_data.split('\n').map(function (x) {return (x=='')||(x.indexOf(',')>0);}).reduce(function (x,y) {return x && y;},true);
    if (!valid) {
        alert("Not all Data lines contain a comma");
        return false;
    }
    if (bot_desc.length<5) {
        alert("Dataset description too short");
        return false;
    }
    if (bot_name.length<2) {
        alert("Bot name cannot be left empty");
        return false;
    }
    if (bot_name.length>50) {
        alert("Bot name too long (max 50 chars)");
        return false;
    }
    valid = bot_name.replace(/^\w+$/, '').length===0;
    if (!valid) {
        alert("Bot name Can only contain letters, numbers and an underscore");
        return false;
    }
    valid=$.ajax({
        type: "GET",
        url: "/bot_exists/"+encodeURI(bot_name),
        cache: false,
        async: false
    }).responseText!="1";
    if (!valid) {
        alert("Bot name already exists");
        return false;
    }
    return true;
}
