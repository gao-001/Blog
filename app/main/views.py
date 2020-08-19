from flask import render_template, redirect, url_for, flash, request, current_app, make_response, abort, jsonify, \
    Response
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm, NewBookmarks
from ..models import User
from .. import db
from flask_login import current_user, login_required
from ..decorators import admin_required, permission_required
from ..models import Role, Post, Permission, Comment, Mark, LinkMark
from flask_sqlalchemy import get_debug_queries
from datetime import datetime
import os


@main.route('/', methods=['GET', 'POST'])
def index():
    post_deploy = Post.query.get_or_404(2)
    post_git = Post.query.get_or_404(1)
    post_flask = Post.query.get_or_404(5)
    post_generate = Post.query.get_or_404(4)
    post_wrapper = Post.query.get_or_404(3)
    form = PostForm()
    if current_user.can(Permission.WRITE) and \
            form.validate_on_submit():
        post = Post(topic=form.topic.data,
                    body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('.index'))
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    page = request.args.get('page', 1, type=int)

    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    return render_template('index.html', show_followed=show_followed,
                           form=form, posts=posts, pagination=pagination,post_deploy=post_deploy,
                           post_git=post_git,post_generate=post_generate,post_flask=post_flask,
                           post_wrapper=post_wrapper)


@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30 * 24 * 60 * 60)  # 30天
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30 * 24 * 60 * 60)  # 30天
    return resp


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts,
                           pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your profile has been updated')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.date = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role
    form.name.data = user.role
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    body_html = request.form['fancy-editormd2-html-code']
    if form.validate_on_submit():
        post.topic = form.topic.data
        post.body = form.body.data
        post.body_html=body_html
        db.session.add(post)
        db.session.commit()
        flash('The post has been updated')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    form.topic.data = post.topic
    return render_template('edit_post.html', form=form, post=post)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    form2 = NewBookmarks()
    if current_user.is_authenticated:
        mark_query = Mark.query.filter_by(author=current_user).join(LinkMark, LinkMark.mark_id == Mark.id).filter(
        LinkMark.post_id == post.id).first()
    else:
        mark_query = False
    query = LinkMark.query.filter_by(post_id=post.id).all()
    if form2.validate_on_submit():
        bookmarks = Mark(name=form2.name.data,
                         author=current_user._get_current_object())
        db.session.add(bookmarks)
        db.session.commit()
        form2.name.data = ''
    if form.validate_on_submit():
        commment = Comment(body=form.body.data,
                           post=post,
                           author=current_user._get_current_object())
        db.session.add(commment)
        db.session.commit()
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
               current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form,
                           comments=comments, pagination=pagination, form2=form2, mark_query=mark_query,
                         )


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    post.delete_post()
    return redirect(url_for('.index'))


@main.route('/delete_comment/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    post_id = comment.post_id
    if current_user != comment.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    comment.delete_comment()
    return redirect(url_for('.post', id=post_id))


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments,
                           pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate', page=request.args.get('page', 1, type=int)))


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASK_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n' %
                (query.statement, query.parameters.query.duration, query.context)
            )
    return response


@main.route('/site_navigation',methods=['GET', 'POST'])
def navigation():
    return render_template('home.html')


@main.route('/editormd')
def editormd():
    return render_template('editormd.html')


@main.route('/new_post', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if current_user.can(Permission.WRITE) and \
            form.validate_on_submit():
        body_html = request.form['fancy-editormd-html-code']
        post = Post(topic=form.topic.data,
                    body=form.body.data,
                    author=current_user._get_current_object(),
                    body_html=body_html,

                    )
        db.session.add(post)
        db.session.commit()
        flash('Post created.', 'success')
        return redirect(url_for('.index'))
    return render_template('new_post.html', form=form)


@main.route('/upload/', methods=['POST'])
@login_required
def upload():
    file = request.files.get('editormd-image-file')
    if not file:
        res = {
            'success': 0,
            'message': '上传失败'
        }
    else:
        ex = os.path.splitext(file.filename)[1]
        filename = datetime.now().strftime('%Y%m%d%H%M%S') + ex
        bodypic_path = 'app/static/images/' + filename
        file.save(bodypic_path)
        res = {
            'success': 1,
            'message': '上传成功',
            'url': url_for('.image', name=filename)
        }
    return jsonify(res)


@main.route('/image/<name>')
def image(name):
    with open(os.path.join('app/static/images/', name), 'rb') as f:
        resp = Response(f.read(), mimetype="image/jpeg")
    return resp


@main.route('/toBookmarks/<int:bookmarks_id>/<int:post_id>', methods=['get', 'post'])
@login_required
def post_to_bookmarks(post_id, bookmarks_id):
    post = Post.query.get_or_404(post_id)
    bookmarks = Mark.query.get_or_404(bookmarks_id)
    mark = LinkMark(mark=bookmarks, post=post)
    db.session.add(mark)
    db.session.commit()
    return redirect(url_for('.post', id=post.id))


@main.route('/canclemark/<int:mark_id>/<int:post_id>/')
def cancel_mark(mark_id, post_id):
    link = LinkMark.query.filter_by(post_id=post_id, mark_id=mark_id).first()
    if link:
        db.session.delete(link)
    db.session.commit()
    return redirect(url_for('main.post',id=post_id))



@main.route('/showbookmarks',methods=['get','post'])
@login_required
def show_bookmarks():
    form = NewBookmarks()
    if form.validate_on_submit():
        bookmarks = Mark(name=form.name.data,
                         author=current_user._get_current_object())
        db.session.add(bookmarks)
        db.session.commit()
        return redirect(url_for('main.show_bookmarks'))
    bookmarks = current_user.marks.all()
    return render_template('show_bookmarks.html', bookmarks=bookmarks,form=form)


@main.route('/deletebookmarks/<int:id>')
def delete_bookmarks(id):
    mark = Mark.query.get_or_404(id)
    db.session.delete(mark)
    db.session.commit()
    return redirect(url_for('main.show_bookmarks'))
