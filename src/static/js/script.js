$(document).ready(function(){
	console.log('window loading');
	$(".task-tile .task-list").mCustomScrollbar({
			theme:"minimal-dark",
			autoHideScrollbar: 0
		});
	$(".modal-card").mCustomScrollbar({
		theme:"minimal-dark",
		autoHideScrollbar: 0
	});
	$(".modal-content").mCustomScrollbar({
		theme:"minimal-dark",
		autoHideScrollbar: 0
	});
	// modal
	$('.modal-button').click(function(){
		var attr = $(this).attr('data-modal');

		// For some browsers, `attr` is undefined; for others, `attr` is false. Check for both.
		if (typeof attr !== typeof undefined && attr !== false) {
		  console.log($(this).data("modal"))
	  		 $('.modal').removeClass('is-active');
		 	 $('html').addClass('is-clipped');
			 $('#' + $(this).data("modal")).addClass('is-active');
			 $('.section.wrapper').addClass('is-active');
		}else
		{
			$('html').addClass('is-clipped');
    		$('.modal').addClass('is-active');
    		$('.section.wrapper').addClass('is-active');
		}
			
		})
	$('.modal-close, .modal-background').click(function($el){
		$('html').removeClass('is-clipped');
		$('.modal').removeClass('is-active');
		$('.section.wrapper').removeClass('is-active');

	}) 
	// tab
	  $('#tab_header ul li.item').on('click', function() {
	    var number = $(this).data('option');
	    $('#tab_header ul li.item').removeClass('is-active');
	    $(this).addClass('is-active');
	    $('.tab_content').removeClass('is-active');
	    $('div[data-item="' + number + '"]').addClass('is-active');
	  });

	//Nav collapse toggle
	$('.navbar-burger').click(function(){
	    $(".navbar-burger").toggleClass("is-active");
      	$(".navbar-menu").toggleClass("is-active");
  	})

  	// dropdown 
  	$('.dropdown').click(function(){
  		$('.dropdown-menu').addClass('has-shadow-dark')
  		$(this).toggleClass('is-active');
  	})

  	// Build Schedule page: collapse toggle balance preview panel 
  	$('#balnce-review').click(function(){
  		$('.balance-review-panel').slideToggle("fast");
  		$(this).find($('i')).toggleClass('fa-caret-down')
  		$(this).find($('i')).toggleClass('fa-caret-right')
  	})

})