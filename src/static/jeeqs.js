// Copyright 2007 Google Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * @fileoverview
 * Javascript code for the interactive AJAX shell.
 *
 * Part of http://code.google.com/p/google-app-engine-samples/.
 *
 * Includes a function (shell.runStatement) that sends the current python
 * statement in the shell prompt text box to the server, and a callback
 * (shell.done) that displays the results when the XmlHttpRequest returns.
 *
 * Also includes cross-browser code (shell.getXmlHttpRequest) to get an
 * XmlHttpRequest.
 */

/**
 * Shell namespace.
 * @type {Object}
 */
var shell = {}

/**
 * The shell history. history is an array of strings, ordered oldest to
 * newest. historyCursor is the current history element that the user is on.
 *
 * The last history element is the statement that the user is currently
 * typing. When a statement is run, it's frozen in the history, a new history
 * element is added to the end of the array for the new statement, and
 * historyCursor is updated to point to the new element.
 *
 * @type {Array}
 */
shell.history = [''];

/**
 * See {shell.history}
 * @type {number}
 */
shell.historyCursor = 0;

/**
 * A constant for the XmlHttpRequest 'done' state.
 * @type Number
 */
shell.DONE_STATE = 4;

/**
 * A cross-browser function to get an XmlHttpRequest object.
 *
 * @return {XmlHttpRequest?} a new XmlHttpRequest
 */
shell.getXmlHttpRequest = function() {
  if (window.XMLHttpRequest) {
    return new XMLHttpRequest();
  } else if (window.ActiveXObject) {
    try {
      return new ActiveXObject('Msxml2.XMLHTTP');
    } catch(e) {
      return new ActiveXObject('Microsoft.XMLHTTP');
    }
  }

  return null;
};

/**
 * Runs the program written in the text area and returns stdout and stderror in "output"
 * text area.
 * @return {Boolean} false to tell the browser not to submit the form.
 */
shell.onRunKeyClick = function(program, isSubmission) {

    isSubmission = (typeof isSubmission == "undefined") ? false: isSubmission;

    var answerForm = document.getElementById('answerForm');

    // build a XmlHttpRequest
    var req = this.getXmlHttpRequest();
    if (!req) {
        return false;
    }

    req.onreadystatechange = function() { shell.doneRunning(req); };

    // build the query parameter string
    var params = '';
    // build the query parameter string
    var value = escape(program).replace(/\+/g, '%2B'); // escape ignores +
    params += '&' + 'program' + '=' + value

    var challenge_key = document.getElementById('challenge_key')
    params += '&' + 'challenge_key' + '=' + challenge_key.value

    if (isSubmission) {
        params += '&is_submission=true'
    }

    // send the request and tell the user.
    req.open("get", "shell.runProgram" + '?' + params, true);
    req.setRequestHeader('Content-type',
        'application/x-www-form-urlencoded;charset=UTF-8');
    req.send(null);
};

/**
 * Runs the program written in the text area and returns stdout and stderror in "output"
 * text area.
 * @return {Boolean} false to tell the browser not to submit the form.
 */
shell.onSubmitKeyClick = function(program) {
    shell.onRunKeyClick(program, true);
};

/**
 * The XmlHttpRequest callback for running the program .
 *
 * @param {XmlHttpRequest} req the XmlHttpRequest we used to send the program to the server
 */
shell.doneRunning = function(req) {
    if (req.readyState == this.DONE_STATE) {

        $('#submitProgramButton').button("option", "label", "Submitted");

        // add the command to the shell output
        var output = document.getElementById('output');

        output.value += '\n >>> Output: ';

        // add the command's result
        var result = req.responseText.replace(/^\s*|\s*$/g, '');  // trim whitespace
        if (result != '')
            output.value += '\n' + result;

       //scroll to bottom [delay is for IE]
      setTimeout(function(){output.scrollTop = output.scrollHeight; }, 10);
    }
};

/**
 * The XmlHttpRequest callback. If the request succeeds, it adds the command
 * and its resulting output to the shell history div.
 *
 * @param {XmlHttpRequest} req the XmlHttpRequest we used to send the current
 *     statement to the server
 */
shell.done = function(req) {
  if (req.readyState == this.DONE_STATE) {
    var statement = document.getElementById('statement')
    statement.className = 'prompt';

    // add the command to the shell output
    var output = document.getElementById('output');

    output.value += '\n>>> ' + statement.value;
    statement.value = '';

    // add a new history element
    this.history.push('');
    this.historyCursor = this.history.length - 1;

    // add the command's result
    var result = req.responseText.replace(/^\s*|\s*$/g, '');  // trim whitespace
    if (result != '')
      output.value += '\n' + result;

    // scroll to the bottom
    output.scrollTop = output.scrollHeight;
    if (output.createTextRange) {
      var range = output.createTextRange();
      range.collapse(false);
      range.select();
    }
  }
};

$('.submit-vote').live('click', function() {

    var $initiator = $(this)

    $submission_id = $(this).attr("id").split("__")[1];
    $response = $('#response__'+$submission_id).val();
    $vote = $(this).siblings('.feedback-buttons').children('.active').val();

    if (!$vote || $response.length < 10) {
        alert('Please enter your vote and a 10 character minimum response!');
        return;
    }

    $(this).addClass("disabled");
    $(this).siblings('.feedback-buttons').children().attr('disabled', 'disabled');

    // Get the in_jeeqs
    $.ajax({
        url: "/rpc",
        async: true,
        type: "GET",
        data: {'method': 'get_in_jeeqs', 'submission_key':$submission_id},
        success: function(response) {
            // The sever sends an HTML
            $('#submissionFeedbacks').html(response);
        },
        error: function(response) {
            $('#submissionFeedbacks').html("Could not retrieve other In Jeeqs")
        }
    })

    $.ajax({
        url: "/rpc",
        async: true,
        type: "POST",
        data: {'method': 'submit_vote', 'submission_key':$submission_id, 'vote':$vote, 'response':$response},
        success: function(response){
            var parsed = jQuery.parseJSON(response)
            if (parsed != null && parsed.flags_left_today == -1) {
                alert("You don't have any more flags left.")
                return;
            }
            if ($vote == "flag") {
                alert("You have " + parsed.flags_left_today + " flags left")
            }

            // Disable the other controls
            $initiator.parent().find("textarea").attr("disabled", "disabled").css("font-style", "italic");
            $initiator.parent().css("background", "bisque");

            $('#submissionFeedbacksContainer').show()
            $('#submissionFeedbacksContainer').insertAfter($initiator.parent())
        }
    })
})

$('.selectable_profile_picture').live('click', function() {
    var $initiator = $(this)
    var $img = $initiator.children('img')
    var $picture_url = $img.attr('src')
    if (!$img.hasClass('current_profile_picture')) {
        $.ajax({
            url: "/rpc",
            async: true,
            type: "POST",
            data: {'method': 'update_profile_picture', 'profile_picture_url':$picture_url},
            success: function(response) {
                $('.selectable_profile_picture').children().removeClass('current_profile_picture')
                $img.addClass('current_profile_picture')
            },
            error: function(response) {
            }
        })
    }
})

$(".challenge_avatars a").on('click', function(event) {
    event.stopPropagation()
    return false;
})


$(document).ready(function() {
    $('a[rel=tooltip]').tooltip()
})

// handle "next"/"previous" buttons for other users' submissions
// Stack of cursors - stores cursors to navigate back in the list of submissions
var challenge_submissions_stack = [];

$(document).on('click', '#challenge_submissions_next, #challenge_submissions_previous', function(event) {
    event.stopPropagation()
    event.preventDefault();

    var challenge_key = $(this).attr('data-challenge_key')
    var cursor = $(this).attr('data-cursor')
    var previous_cursor = $(this).attr('data-previous_cursor')
    var isNext = $(this).attr('id') == 'challenge_submissions_next' ? true : false

    if (isNext) {
        challenge_submissions_stack.push(previous_cursor);
    }
    else {
        if (challenge_submissions_stack.length > 0) {
            cursor = challenge_submissions_stack.pop()
        }
        else {
            $(this).css('display', 'none');
            return;
        }
    }

    $('#other_submissions').html('Loading ... ')
    $.ajax({
        url: "/review/?ch=" + challenge_key + "&cursor=" + cursor,
        async: true,
        type: "GET",
        success: function(response) {
            $('#other_submissions').html(response);
            review_page_loaded = true
        },
        error: function(response) {
            $('#other_submissions').html('An Error occurred while loading this page. Please try again later ...');
        }
    })
});

// stores cursors to be able to navigate back in a list of recent attempts
var attempts_cursors_stack = [];

// handle 'newer'/'older' buttons in the list of your recent attempts
// on a challenge page
$(document).on('click', '#attempts_older', function(event) {
    event.stopPropagation();
    event.preventDefault();
    var challenge_key = $(this).attr('data-challenge_key');
    var cursor = $(this).attr('data-cursor');

    // store cursor to be able to navigate back to the beginning of the list
    // by pressing "Newer"
    attempts_cursors_stack.push(cursor);
    ajax_fetch_attempts(challenge_key, cursor);
});

$(document).on('click', '#attempts_newer', function(event) {
    event.stopPropagation();
    event.preventDefault();
    var challenge_key = $(this).attr('data-challenge_key');

    // stack top contains cursor for the current page:
    // on loading 'newer' we discard that cursor on top of the stack and pass
    // the one below it (for the page containing newer attempts) to the server
    attempts_cursors_stack.pop();
    var cursor;
    if(attempts_cursors_stack.length > 0) {
        cursor = attempts_cursors_stack[attempts_cursors_stack.length - 1];
    } else {
        // We've got nothing left at the stack, meaning we should display
        // the first page - denoted by cursor value of 'None'
        cursor = 'None';
    }
    ajax_fetch_attempts(challenge_key, cursor);
});

function ajax_fetch_attempts (challenge_key, cursor) {
    $.ajax({
        url: "/attempts/?ch=" + challenge_key + "&cursor=" + cursor,
        async: true,
        type: "GET",
        success: function(response) {
            $('#recent-attempt-contents').html(response);
            review_page_loaded = true
        },
        error: function(response) {
            $('#recent-attempt-contents').html('An Error occurred while loading this page. Please try again later ...');
        }
    })
}

$(document).ready(function() {
    $("#updateDisplayName").button().bind('click', function() {
        $displayname = $('#displayname').val();
        $(this).button("option", "label", "...");
        $initiator = $(this);

        $.ajax({
            url: "/rpc",
            async: false,
            type: "POST",
            data: {'method': 'update_displayname', 'display_name':$displayname},
            success: function(response){
                if (response == 'success') {
                    $initiator.button('Your display name has been updated');
                }
                else if (response == 'no_operation') {
                    $initiator.button('You are already using this display name.');
                }
                else if (response == 'not_unique') {
                    $initiator.button('This display name is in use by another user!');
                }
            },
            error: function(response) {
                $initiator.button('error');
            }
        })

    });
})
