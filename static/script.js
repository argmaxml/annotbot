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

$("#txt_botname").on("change", function () {document.getElementById("spn_botname").textContent=document.getElementById("txt_botname").value;})

function validate() {
    var valid = true;
    valid = document.getElementById("txt_classes").value.split('\n').map(function (x) {return (x.length<10);}).reduce(function (x,y) {return x && y;},true);
    if (!valid) {
        alert("Class name cannot be longer than 10 characters");
        return false;
    }
    valid = document.getElementById("txt_data").value.split('\n').map(function (x) {return (x=='')||(x.indexOf(',')>0);}).reduce(function (x,y) {return x && y;},true);
    if (!valid) {
        alert("Not all Data lines contain a comma");
        return false;
    }
    valid = document.getElementById("txt_desc").value.length>5;
    if (!valid) {
        alert("Dataset description too short");
        return false;
    }
    valid = document.getElementById("txt_botname").value.length<2;
    if (!valid) {
        alert("Bot name description too short");
        return false;
    }
    valid = document.getElementById("txt_botname").value.length>20;
    if (!valid) {
        alert("Bot name description too long");
        return false;
    }
    valid = document.getElementById("txt_botname").value.replace(/^\w+$/, '').length==0;
    if (!valid) {
        alert("Bot name Can only contain letters, numbers and an underscore");
        return false;
    }
    valid=$.ajax({
        type: "GET",
        url: "/bot_exists/"+encodeURI(document.getElementById("txt_botname").value),
        cache: false,
        async: false
    }).responseText!="1";
    if (!valid) {
        alert("Bot name already exists");
        return false;
    }
    return true;
}
